"""
成员维度 API(均作用于当前登录用户的数据空间)

- GET    /api/members            列出成员
- POST   /api/members            新增成员 {name, color?}
- PUT    /api/members/<id>       修改成员 {name?, color?}
- DELETE /api/members/<id>       删除成员(名下文件回落默认成员)
"""
import logging
from flask import Blueprint, jsonify, request

from utils.session import get_current_uid
from services import members as member_svc

logger = logging.getLogger(__name__)
members_bp = Blueprint('members', __name__)


def _uid():
    return get_current_uid() or '__anon__'


@members_bp.route('/api/members', methods=['GET'])
def list_members():
    return jsonify({'success': True, 'members': member_svc.list_members(_uid())})


@members_bp.route('/api/members', methods=['POST'])
def add_member():
    data = request.get_json(silent=True) or {}
    try:
        m = member_svc.add_member(_uid(), data.get('name', ''), data.get('color'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'member': m})


@members_bp.route('/api/members/<member_id>', methods=['PUT'])
def update_member(member_id):
    data = request.get_json(silent=True) or {}
    try:
        m = member_svc.update_member(_uid(), member_id, data.get('name'), data.get('color'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'member': m})


@members_bp.route('/api/members/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    try:
        member_svc.delete_member(_uid(), member_id)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True})
