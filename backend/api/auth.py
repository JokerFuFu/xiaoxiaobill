"""
鉴权 + 用户管理 API

- POST /api/auth/login         登录
- POST /api/auth/logout        登出
- GET  /api/auth/me            当前用户
- POST /api/auth/password      修改自己的密码
- GET  /api/admin/users        列出用户(管理员)
- POST /api/admin/users        创建用户(管理员)
- DELETE /api/admin/users/<id> 删除用户(管理员)
- POST /api/admin/users/<id>/password  重置某用户密码(管理员)
"""
import logging
from functools import wraps
from flask import Blueprint, jsonify, request, session
from flask_login import login_user, logout_user, login_required, current_user

from services import auth as auth_svc

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


def admin_required(f):
    """管理员双重校验(纵深防御,不只依赖 before_request 的路径前缀拦截)。"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': '未登录', 'code': 'AUTH_REQUIRED'}), 401
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return wrapper


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')
    user = auth_svc.verify_login(username, password)
    if not user:
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
    # 登录前清掉演示态,避免数据空间串台
    session.pop('is_demo', None)
    login_user(user, remember=True)
    logger.info(f"用户登录: {user.username} ({user.id})")
    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    logout_user()
    session.pop('is_demo', None)
    return jsonify({'success': True})


@auth_bp.route('/api/auth/me')
def me():
    if session.get('is_demo'):
        return jsonify({'success': True, 'authenticated': True, 'is_demo': True,
                        'user': {'id': 'demo_user', 'username': 'demo', 'display_name': '演示账号',
                                 'role': 'user', 'is_admin': False}})
    if current_user.is_authenticated:
        return jsonify({'success': True, 'authenticated': True, 'is_demo': False,
                        'user': current_user.to_dict()})
    return jsonify({'success': True, 'authenticated': False})


@auth_bp.route('/api/auth/password', methods=['POST'])
@login_required
def change_my_password():
    data = request.get_json(silent=True) or {}
    old = data.get('old_password', '')
    new = data.get('new_password', '')
    if not auth_svc.verify_login(current_user.username, old):
        return jsonify({'success': False, 'error': '原密码错误'}), 400
    try:
        auth_svc.set_password(current_user.id, new)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True})


# ============ 管理员:用户管理 ============
@auth_bp.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_list_users():
    return jsonify({'success': True, 'users': auth_svc.list_users()})


@auth_bp.route('/api/admin/users', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    data = request.get_json(silent=True) or {}
    try:
        u = auth_svc.create_user(
            data.get('username', ''), data.get('password', ''),
            display_name=data.get('display_name'), role=data.get('role', 'user'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'user': u.to_dict()})


@auth_bp.route('/api/admin/users/<uid>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(uid):
    if uid == current_user.id:
        return jsonify({'success': False, 'error': '不能删除当前登录账号'}), 400
    try:
        auth_svc.delete_user(uid)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True})


@auth_bp.route('/api/admin/users/<uid>/password', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(uid):
    data = request.get_json(silent=True) or {}
    try:
        auth_svc.set_password(uid, data.get('password', ''))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True})
