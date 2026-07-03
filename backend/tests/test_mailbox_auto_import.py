import services.auth as auth
import services.mailbox as mailbox


def _fake_mail(mail_uid, attachments):
    return {'uid': mail_uid, 'subject': 's', 'sender': 'x', 'date': 'd',
            'attachments': attachments, 'imported_files': []}


def test_auto_import_one_imports_non_password_attachment(mail_uid, monkeypatch):
    uid = mail_uid
    mail = _fake_mail('1', [{'index': 0, 'filename': 'bill.csv', 'size': 10, 'is_zip': False}])
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])
    calls = []

    def fake_import(u, mail_uid, idx, zip_password=None, member_id=None, session_dir=None):
        calls.append((mail_uid, idx))
        return {'files': ['bill.csv']}

    monkeypatch.setattr(mailbox, 'import_attachment', fake_import)

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 1, 'pending': 0, 'error': None}
    assert calls == [('1', 0)]


def test_auto_import_one_marks_encrypted_zip_as_pending(mail_uid, monkeypatch):
    uid = mail_uid
    mail = _fake_mail('2', [{'index': 0, 'filename': 'bill.zip', 'size': 10, 'is_zip': True}])
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])

    def fake_import(u, mail_uid, idx, zip_password=None, member_id=None, session_dir=None):
        raise mailbox.PasswordRequired('压缩包密码错误或未提供(支付宝/微信的账单包需要密码)')

    monkeypatch.setattr(mailbox, 'import_attachment', fake_import)

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 0, 'pending': 1, 'error': None}
    assert mailbox.pending_count(uid) == 1


def test_auto_import_one_skips_already_done_and_already_pending(mail_uid, monkeypatch):
    uid = mail_uid
    mail = _fake_mail('3', [
        {'index': 0, 'filename': 'a.csv', 'size': 10, 'is_zip': False},
        {'index': 1, 'filename': 'b.zip', 'size': 10, 'is_zip': True},
    ])
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])

    imported = mailbox._load_imported(uid)
    imported['3'] = {'files': ['a.csv'], 'at': 'x', 'indices': [0]}
    mailbox._save_imported(uid, imported)
    mailbox._mark_pending(uid, '3', mail, mail['attachments'][1])

    calls = []
    monkeypatch.setattr(mailbox, 'import_attachment',
                        lambda *a, **k: calls.append(a) or {'files': []})

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 0, 'pending': 0, 'error': None}
    assert calls == []


def test_auto_import_one_records_error_when_fetch_fails(mail_uid, monkeypatch):
    uid = mail_uid

    def boom(u, days=90):
        raise ValueError('邮箱未配置完整(服务器/邮箱地址/授权码)')

    monkeypatch.setattr(mailbox, 'fetch_bills', boom)

    result = mailbox.auto_import_one(uid)

    assert result['imported'] == 0
    assert '邮箱未配置完整' in result['error']
    status = mailbox._load_auto_status(uid)
    assert '邮箱未配置完整' in status['last_error']


def test_auto_import_all_skips_disabled_and_isolates_failures(mail_uid, monkeypatch):
    monkeypatch.setattr(auth, 'list_users', lambda: [
        {'id': 'u1'}, {'id': 'u2'}, {'id': 'u3'},
    ])
    mailbox.save_config('u1', host='imap.qq.com', port=993, address='a@qq.com', auth_code='c',
                        auto_import=True)
    mailbox.save_config('u2', host='imap.qq.com', port=993, address='b@qq.com', auth_code='c',
                        auto_import=True)
    mailbox.save_config('u3', host='imap.qq.com', port=993, address='c@qq.com', auth_code='c',
                        auto_import=False)

    calls = []

    def fake_auto_import_one(uid, days=None):
        calls.append(uid)
        if uid == 'u1':
            raise RuntimeError('模拟 u1 自动导入崩了')
        return {'imported': 0, 'pending': 0, 'error': None}

    monkeypatch.setattr(mailbox, 'auto_import_one', fake_auto_import_one)

    mailbox.auto_import_all()

    assert calls == ['u1', 'u2']
    status_u1 = mailbox._load_auto_status('u1')
    assert '异常' in status_u1['last_error']
