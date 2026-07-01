import services.mailbox as mailbox


def test_save_config_default_auto_import_is_false(mail_uid):
    uid = mail_uid
    cfg = mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')
    assert cfg['auto_import'] is False


def test_save_config_persists_auto_import_true(mail_uid):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')
    cfg = mailbox.save_config(uid, auto_import=True)
    assert cfg['auto_import'] is True


def test_save_config_without_auto_import_keeps_old_value(mail_uid):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code',
                        auto_import=True)
    cfg = mailbox.save_config(uid, port=993)
    assert cfg['auto_import'] is True


def test_public_config_exposes_auto_import_and_status_fields(mail_uid):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code',
                        auto_import=True)
    mailbox._mark_pending(uid, '1', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'a.zip'})
    mailbox._save_auto_status(uid, ok=False, error='测试错误')

    pub = mailbox.public_config(uid)
    assert pub['auto_import'] is True
    assert pub['pending_count'] == 1
    assert pub['last_error'] == '测试错误'
    assert pub['last_run_at']
