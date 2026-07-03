"""
加密银行 PDF 处理测试:
- PasswordRequired 异常(加密 zip / 加密 PDF 共用,用于把附件记入待处理队列)
- _decrypt_pdf_if_needed:加密 PDF 用密码解密,未加密原样返回,打不开抛 PasswordRequired
- import_attachment:加密 PDF 无密码抛 PasswordRequired、有密码落盘解密版
- auto_import_one:加密 PDF(非 zip)也记入待处理
"""
import io
import os

import pytest
import pikepdf
import pyzipper

import services.mailbox as mailbox


# ---------- 构造测试 PDF ----------
def _plain_pdf():
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(300, 300))
    b = io.BytesIO()
    pdf.save(b)
    return b.getvalue()


def _encrypted_pdf(pw):
    b = io.BytesIO()
    with pikepdf.open(io.BytesIO(_plain_pdf())) as pdf:
        pdf.save(b, encryption=pikepdf.Encryption(owner=pw, user=pw))
    return b.getvalue()


def _opens_with_empty_password(raw):
    """能用空密码打开 => 未加密(已解密)。"""
    with pikepdf.open(io.BytesIO(raw)):
        return True


def _aes_zip(pw, name='bill.csv', data=b'a,b,c'):
    zbuf = io.BytesIO()
    with pyzipper.AESZipFile(zbuf, 'w', encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(pw.encode())
        zf.writestr(name, data)
    return zbuf.getvalue()


# ---------- PasswordRequired ----------
def test_password_required_is_valueerror_subclass():
    assert issubclass(mailbox.PasswordRequired, ValueError)


def test_extract_zip_bad_password_raises_password_required():
    z = _aes_zip('right')
    with pytest.raises(mailbox.PasswordRequired):
        mailbox._extract_zip(z, 'wrong')


# ---------- _decrypt_pdf_if_needed ----------
def test_decrypt_pdf_plain_returns_openable():
    out = mailbox._decrypt_pdf_if_needed(_plain_pdf(), None)
    assert _opens_with_empty_password(out)


def test_decrypt_pdf_encrypted_no_password_raises():
    with pytest.raises(mailbox.PasswordRequired):
        mailbox._decrypt_pdf_if_needed(_encrypted_pdf('secret'), None)


def test_decrypt_pdf_encrypted_wrong_password_raises():
    with pytest.raises(mailbox.PasswordRequired):
        mailbox._decrypt_pdf_if_needed(_encrypted_pdf('secret'), 'nope')


def test_decrypt_pdf_encrypted_correct_password_decrypts():
    out = mailbox._decrypt_pdf_if_needed(_encrypted_pdf('secret'), 'secret')
    assert _opens_with_empty_password(out)  # 解密后空密码即可打开


def test_decrypt_pdf_non_pdf_bytes_falls_back_to_raw():
    """非 PDF/pikepdf 打不开(非密码原因)的字节:原样返回,不误伤、不抛 PasswordRequired。"""
    junk = b'this is not a pdf at all'
    assert mailbox._decrypt_pdf_if_needed(junk, None) == junk


# ---------- import_attachment 集成(monkeypatch IMAP) ----------
class _DummyPart:
    def __init__(self, data):
        self._data = data

    def get_payload(self, decode=False):
        return self._data


def _setup(uid, tmp_path, monkeypatch, filename, payload):
    session_dir = os.path.join(str(tmp_path), uid)
    os.makedirs(session_dir, exist_ok=True)
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')

    class DummyM:
        def select(self, *a, **k):
            return ('OK', [b'1'])

        def logout(self):
            pass

    monkeypatch.setattr(mailbox, '_connect', lambda cfg: DummyM())
    monkeypatch.setattr(mailbox, '_fetch_msg', lambda M, mail_uid: object())
    monkeypatch.setattr(mailbox, '_iter_attachments',
                        lambda msg: [(0, filename, len(payload), _DummyPart(payload))])
    return session_dir


def test_import_encrypted_pdf_without_password_raises(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    sd = _setup(uid, tmp_path, monkeypatch, 'boc.pdf', _encrypted_pdf('secret'))
    with pytest.raises(mailbox.PasswordRequired):
        mailbox.import_attachment(uid, '100', 0, session_dir=sd)


def test_import_encrypted_pdf_with_password_saves_decrypted(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    sd = _setup(uid, tmp_path, monkeypatch, 'boc.pdf', _encrypted_pdf('secret'))
    res = mailbox.import_attachment(uid, '100', 0, zip_password='secret', session_dir=sd)
    assert res['files'] == ['boc.pdf']
    with open(os.path.join(sd, 'boc.pdf'), 'rb') as f:
        assert _opens_with_empty_password(f.read())  # 落盘的是解密版


def test_import_plain_pdf_unchanged(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    sd = _setup(uid, tmp_path, monkeypatch, 'stmt.pdf', _plain_pdf())
    res = mailbox.import_attachment(uid, '100', 0, session_dir=sd)
    assert res['files'] == ['stmt.pdf']
    with open(os.path.join(sd, 'stmt.pdf'), 'rb') as f:
        assert _opens_with_empty_password(f.read())


def test_imported_bill_file_is_0600(mail_uid, tmp_path, monkeypatch):
    """账单(尤其解密后的明文银行 PDF)落盘应为 0600,与项目敏感文件约定一致。"""
    import stat
    uid = mail_uid
    sd = _setup(uid, tmp_path, monkeypatch, 'boc.pdf', _encrypted_pdf('secret'))
    mailbox.import_attachment(uid, '100', 0, zip_password='secret', session_dir=sd)
    mode = stat.S_IMODE(os.stat(os.path.join(sd, 'boc.pdf')).st_mode)
    assert mode == 0o600


# ---------- auto_import_one:加密 PDF(非 zip)也进待处理 ----------
def test_auto_import_one_marks_encrypted_pdf_as_pending(mail_uid, monkeypatch):
    uid = mail_uid
    mail = {'uid': '7', 'subject': '中国银行交易流水', 'sender': 'boc', 'date': 'd',
            'attachments': [{'index': 0, 'filename': 'boc.pdf', 'size': 10, 'is_zip': False}],
            'imported_files': []}
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])

    def fake_import(u, mail_uid, idx, zip_password=None, member_id=None, session_dir=None):
        raise mailbox.PasswordRequired('PDF 已加密,需要打开密码')

    monkeypatch.setattr(mailbox, 'import_attachment', fake_import)

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 0, 'pending': 1, 'error': None}
    assert mailbox.pending_count(uid) == 1
