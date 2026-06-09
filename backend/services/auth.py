"""
用户/鉴权服务

纯文件 JSON 存储(data/users.json)+ werkzeug 密码哈希 + Flask-Login User。
不引入数据库,贴合本项目"无 DB·纯文件"架构;鉴权流程(session/login_required/current_user)
交给成熟的 Flask-Login 处理,不自造轮子。
"""
import os
import json
import logging
import threading
from datetime import datetime
from secrets import token_hex

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from config import USERS_FILE, DATA_DIR, BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_PASSWORD, BOOTSTRAP_ADMIN_DISPLAY

logger = logging.getLogger(__name__)
_lock = threading.RLock()


def _load():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取 users.json 失败: {e}")
        return {}


def _save(d):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = USERS_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USERS_FILE)        # 原子写,避免并发损坏


class User(UserMixin):
    """Flask-Login 用户对象,包裹 users.json 中的一条记录。"""
    def __init__(self, uid, rec):
        self.id = uid
        self.username = rec.get('username', uid)
        self.display_name = rec.get('display_name', self.username)
        self.role = rec.get('role', 'user')
        self.created_at = rec.get('created_at', '')

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id, 'username': self.username, 'display_name': self.display_name,
            'role': self.role, 'created_at': self.created_at, 'is_admin': self.is_admin,
        }


def get_user(uid):
    rec = _load().get(uid)
    return User(uid, rec) if rec else None


def verify_login(username, password):
    """用户名+密码校验,成功返回 User,失败 None。"""
    for uid, rec in _load().items():
        if rec.get('username', '').lower() == (username or '').lower():
            if check_password_hash(rec.get('password_hash', ''), password or ''):
                return User(uid, rec)
            return None
    return None


def list_users():
    return [User(uid, rec).to_dict() for uid, rec in sorted(_load().items(), key=lambda kv: kv[1].get('created_at', ''))]


def create_user(username, password, display_name=None, role='user', uid=None):
    username = (username or '').strip()
    if not username:
        raise ValueError('用户名不能为空')
    if not password or len(password) < 4:
        raise ValueError('密码至少 4 位')
    if role not in ('admin', 'user'):
        role = 'user'
    with _lock:
        d = _load()
        if any(r.get('username', '').lower() == username.lower() for r in d.values()):
            raise ValueError('用户名已存在')
        uid = uid or ('u_' + token_hex(4))
        d[uid] = {
            'username': username,
            'password_hash': generate_password_hash(password),
            'display_name': (display_name or username).strip(),
            'role': role,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        _save(d)
        logger.info(f"创建用户 {username} ({uid}) role={role}")
        return get_user(uid)


def set_password(uid, password):
    if not password or len(password) < 4:
        raise ValueError('密码至少 4 位')
    with _lock:
        d = _load()
        if uid not in d:
            raise ValueError('用户不存在')
        d[uid]['password_hash'] = generate_password_hash(password)
        _save(d)
        return True


def delete_user(uid):
    with _lock:
        d = _load()
        if uid not in d:
            raise ValueError('用户不存在')
        admins = [u for u, r in d.items() if r.get('role') == 'admin']
        if d[uid].get('role') == 'admin' and len(admins) <= 1:
            raise ValueError('不能删除唯一的管理员')
        del d[uid]
        _save(d)
        logger.info(f"删除用户 {uid}")
        return True


def ensure_admin():
    """首次启动 bootstrap:无任何账号时创建管理员。
    uid 固定为 'user_local',让既有的 upload/user_local 数据归属到管理员名下(无缝迁移)。"""
    if _load():
        return
    try:
        create_user(BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_PASSWORD,
                    display_name=BOOTSTRAP_ADMIN_DISPLAY, role='admin', uid='user_local')
        logger.info(f"已 bootstrap 管理员账号: {BOOTSTRAP_ADMIN_USERNAME} (uid=user_local)")
    except Exception as e:
        logger.error(f"bootstrap 管理员失败: {e}")
