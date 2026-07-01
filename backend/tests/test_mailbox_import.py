import os

import services.mailbox as mailbox


class _DummyPart:
    def __init__(self, data):
        self._data = data

    def get_payload(self, decode=False):
        return self._data


def _setup_mail_env(uid, tmp_path, monkeypatch, filename='bill.csv', payload=b'a,b,c'):
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


def test_import_attachment_records_index(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    session_dir = _setup_mail_env(uid, tmp_path, monkeypatch)

    result = mailbox.import_attachment(uid, '100', 0, session_dir=session_dir)

    assert result['files'] == ['bill.csv']
    imported = mailbox._load_imported(uid)
    assert imported['100']['indices'] == [0]


def test_import_attachment_clears_matching_pending_entry(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    session_dir = _setup_mail_env(uid, tmp_path, monkeypatch)
    # 先假装这个附件之前需要密码、被记入待处理
    mailbox._mark_pending(uid, '100', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'bill.zip'})
    assert mailbox.pending_count(uid) == 1

    mailbox.import_attachment(uid, '100', 0, session_dir=session_dir)

    assert mailbox.pending_count(uid) == 0


def test_import_attachment_does_not_touch_other_mails_pending(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    session_dir = _setup_mail_env(uid, tmp_path, monkeypatch)
    mailbox._mark_pending(uid, '999', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'other.zip'})

    mailbox.import_attachment(uid, '100', 0, session_dir=session_dir)

    assert mailbox.pending_count(uid) == 1  # 邮件 999 的待处理记录不受影响
