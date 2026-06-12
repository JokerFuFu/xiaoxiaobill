"""
邮箱取账单 API。

- GET  /api/mail/config            配置(授权码只回传布尔) + 服务商预设
- POST /api/mail/config            保存 {host, port, address, auth_code?(''=清除)}
- POST /api/mail/test              测试连接
- POST /api/mail/fetch             拉取账单邮件 {days}
- POST /api/mail/import            导入附件 {uid, index, zip_password?, member_id?}
"""
import logging

from flask import Blueprint, abort, jsonify, request

from utils.session import get_current_uid, get_session_dir
from services import mailbox as mail_svc

logger = logging.getLogger(__name__)
mail_bp = Blueprint('mail', __name__)


def _uid():
    uid = get_current_uid()
    if not uid:
        abort(401)
    return uid


@mail_bp.route('/api/mail/config', methods=['GET'])
def get_config():
    return jsonify({'success': True, 'config': mail_svc.public_config(_uid())})


@mail_bp.route('/api/mail/config', methods=['POST'])
def save_config():
    data = request.get_json(silent=True) or {}
    host = (data.get('host') or '').strip()
    address = (data.get('address') or '').strip()
    if host and not all(c.isalnum() or c in '.-' for c in host):
        return jsonify({'success': False, 'error': '服务器地址格式不对'}), 400
    if address and '@' not in address:
        return jsonify({'success': False, 'error': '邮箱地址格式不对'}), 400
    mail_svc.save_config(_uid(), host=host or None, port=data.get('port'),
                         address=address or None, auth_code=data.get('auth_code'))
    return jsonify({'success': True, 'config': mail_svc.public_config(_uid())})


@mail_bp.route('/api/mail/test', methods=['POST'])
def test():
    try:
        r = mail_svc.test_config(_uid())
    except ValueError as e:
        return jsonify({'success': True, 'ok': False, 'message': str(e)})
    except Exception as e:
        logger.exception("邮箱测试失败")
        return jsonify({'success': True, 'ok': False, 'message': f'连接失败: {str(e)[:80]}'})
    return jsonify({'success': True, **r})


@mail_bp.route('/api/mail/fetch', methods=['POST'])
def fetch():
    data = request.get_json(silent=True) or {}
    days = data.get('days', 90)
    try:
        mails = mail_svc.fetch_bills(_uid(), days=days)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception("拉取账单邮件失败")
        return jsonify({'success': False, 'error': f'拉取失败: {str(e)[:80]}'}), 500
    return jsonify({'success': True, 'mails': mails})


@mail_bp.route('/api/mail/import', methods=['POST'])
def import_att():
    data = request.get_json(silent=True) or {}
    mail_uid = str(data.get('uid') or '').strip()
    if not mail_uid.isdigit():
        return jsonify({'success': False, 'error': '邮件标识不合法'}), 400
    try:
        att_index = int(data.get('index'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '附件序号不合法'}), 400
    try:
        r = mail_svc.import_attachment(
            _uid(), mail_uid, att_index,
            zip_password=(data.get('zip_password') or '').strip() or None,
            member_id=(data.get('member_id') or '').strip() or None,
            session_dir=get_session_dir())
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception("邮件附件导入失败")
        return jsonify({'success': False, 'error': f'导入失败: {str(e)[:80]}'}), 500
    return jsonify({'success': True, **r})
