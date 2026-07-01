"""
邮箱自动导入相关测试的共享 fixture。
"""
import pytest

import services.mailbox as mailbox


@pytest.fixture
def mail_uid(tmp_path, monkeypatch):
    """把 mailbox 模块的 UPLOAD_FOLDER 打到临时目录,测试之间互不干扰,
    也不会碰到真实的 backend/data/upload/。返回一个测试用 uid 字符串。"""
    monkeypatch.setattr(mailbox, 'UPLOAD_FOLDER', str(tmp_path))
    return 'test_user'
