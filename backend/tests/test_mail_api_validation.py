import services.mailbox as mailbox


def test_validate_auto_import_request_blocks_when_incomplete():
    err = mailbox.validate_auto_import_request(True, '', 'a@qq.com', 'code')
    assert err == '请先完整配置邮箱(服务器/地址/授权码)再开启自动导入'


def test_validate_auto_import_request_allows_when_complete():
    assert mailbox.validate_auto_import_request(True, 'imap.qq.com', 'a@qq.com', 'code') is None


def test_validate_auto_import_request_ignores_when_turning_off():
    assert mailbox.validate_auto_import_request(False, '', '', '') is None
