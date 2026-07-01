from flask import Flask

import api.mail as mail_api
import services.mailbox as mailbox


def test_validate_auto_import_request_blocks_when_incomplete():
    err = mailbox.validate_auto_import_request(True, '', 'a@qq.com', 'code')
    assert err == '请先完整配置邮箱(服务器/地址/授权码)再开启自动导入'


def test_validate_auto_import_request_allows_when_complete():
    assert mailbox.validate_auto_import_request(True, 'imap.qq.com', 'a@qq.com', 'code') is None


def test_validate_auto_import_request_ignores_when_turning_off():
    assert mailbox.validate_auto_import_request(False, '', '', '') is None


def _ctx(payload):
    """构造一个裸的 Flask 请求上下文,直接调用路由视图函数(不走真实鉴权/蓝图注册)。"""
    return Flask(__name__).test_request_context('/api/mail/config', method='POST', json=payload)


def test_route_blocks_enabling_autoimport_while_clearing_auth(monkeypatch):
    """回归测试:单请求 {auto_import:true, auth_code:''} 不应该"先用旧授权码通过校验、
    再把授权码清空"——这会产生"自动导入开启但无授权码"的非法状态。"""
    called = {}
    monkeypatch.setattr(mail_api, 'get_current_uid', lambda: 'test_user')
    monkeypatch.setattr(mail_api.mail_svc, 'load_config',
                         lambda uid: {'host': 'imap.qq.com', 'address': 'a@qq.com', 'auth_code': 'oldcode'})
    monkeypatch.setattr(mail_api.mail_svc, 'save_config',
                         lambda *a, **k: called.setdefault('yes', True) or {})
    with _ctx({'auto_import': True, 'auth_code': ''}):
        resp = mail_api.save_config()
    # 错误路径返回 (jsonify(...), 400)
    assert isinstance(resp, tuple) and resp[1] == 400
    assert 'yes' not in called  # save_config 不应该被执行


def test_route_blocks_enabling_autoimport_while_auth_is_whitespace(monkeypatch):
    """授权码为纯空白同样应被视为"清空",而不是绕过校验的有效值。"""
    called = {}
    monkeypatch.setattr(mail_api, 'get_current_uid', lambda: 'test_user')
    monkeypatch.setattr(mail_api.mail_svc, 'load_config',
                         lambda uid: {'host': 'imap.qq.com', 'address': 'a@qq.com', 'auth_code': 'oldcode'})
    monkeypatch.setattr(mail_api.mail_svc, 'save_config',
                         lambda *a, **k: called.setdefault('yes', True) or {})
    with _ctx({'auto_import': True, 'auth_code': '   '}):
        resp = mail_api.save_config()
    assert isinstance(resp, tuple) and resp[1] == 400
    assert 'yes' not in called


def test_route_allows_enabling_autoimport_with_existing_valid_auth(monkeypatch):
    """未提供 auth_code 字段时,应沿用已保存的授权码继续校验,不应被误判为清空。"""
    saved = {}
    monkeypatch.setattr(mail_api, 'get_current_uid', lambda: 'test_user')
    monkeypatch.setattr(mail_api.mail_svc, 'load_config',
                         lambda uid: {'host': 'imap.qq.com', 'address': 'a@qq.com', 'auth_code': 'oldcode'})
    monkeypatch.setattr(mail_api.mail_svc, 'save_config',
                         lambda *a, **k: saved.setdefault('kw', k) or {})
    monkeypatch.setattr(mail_api.mail_svc, 'public_config', lambda uid: {})
    with _ctx({'auto_import': True}):
        resp = mail_api.save_config()
    # 成功路径返回单个 Response(不是 400 元组)
    assert not (isinstance(resp, tuple) and len(resp) == 2 and resp[1] == 400)
    assert saved.get('kw', {}).get('auto_import') is True


def test_route_allows_clearing_auth_when_autoimport_not_enabling(monkeypatch):
    """单独清空授权码(不涉及开启自动导入)时,清空仍应被允许。"""
    saved = {}
    monkeypatch.setattr(mail_api, 'get_current_uid', lambda: 'test_user')
    monkeypatch.setattr(mail_api.mail_svc, 'load_config',
                         lambda uid: {'host': 'imap.qq.com', 'address': 'a@qq.com', 'auth_code': 'oldcode',
                                      'auto_import': False})
    monkeypatch.setattr(mail_api.mail_svc, 'save_config',
                         lambda *a, **k: saved.setdefault('kw', k) or {})
    monkeypatch.setattr(mail_api.mail_svc, 'public_config', lambda uid: {})
    with _ctx({'auth_code': ''}):
        resp = mail_api.save_config()
    assert not (isinstance(resp, tuple) and len(resp) == 2 and resp[1] == 400)
    assert saved.get('kw', {}).get('auth_code') == ''
