"""
资产负债 API —— 三表模型中的「资产负债表」。

- GET    /api/networth                     总览:账户、快照、净资产趋势、解释表
- POST   /api/networth/accounts            新增账户 {name, type}
- PUT    /api/networth/accounts/<aid>      改名/改类型
- DELETE /api/networth/accounts/<aid>      删除账户(连带各快照中该账户余额)
- POST   /api/networth/snapshots           记/改一笔快照 {date, balances:{aid:val}, note}
- DELETE /api/networth/snapshots/<date>    删除某天快照
"""
import logging

from flask import Blueprint, abort, jsonify, request

from utils.session import get_current_uid
from services import networth as nw_svc
from services.data_loader import load_alipay_data

logger = logging.getLogger(__name__)
networth_bp = Blueprint('networth', __name__)


def _uid():
    uid = get_current_uid()
    if not uid:
        abort(401)   # fail-closed:不落入共享匿名空间
    return uid


def _overview(uid):
    df = None
    try:
        df = load_alipay_data()
    except FileNotFoundError:
        pass
    except Exception:
        logger.exception("networth 读取流水失败(不影响快照展示)")
    return {
        'accounts': nw_svc.list_accounts(uid),
        'account_types': nw_svc.ACCOUNT_TYPES,
        'liability_types': sorted(nw_svc.LIABILITY_TYPES),
        'snapshots': nw_svc.list_snapshots(uid),
        'trend': nw_svc.trend(uid),
        'explain': nw_svc.explain(uid, df),
    }


@networth_bp.route('/api/networth')
def overview():
    return jsonify({'success': True, **_overview(_uid())})


@networth_bp.route('/api/networth/accounts', methods=['POST'])
def add_account():
    data = request.get_json(silent=True) or {}
    try:
        acc = nw_svc.add_account(_uid(), data.get('name'), data.get('type'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'account': acc, **_overview(_uid())})


@networth_bp.route('/api/networth/accounts/<aid>', methods=['PUT'])
def update_account(aid):
    data = request.get_json(silent=True) or {}
    try:
        nw_svc.update_account(_uid(), aid, name=data.get('name'), type_=data.get('type'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, **_overview(_uid())})


@networth_bp.route('/api/networth/accounts/<aid>', methods=['DELETE'])
def delete_account(aid):
    nw_svc.delete_account(_uid(), aid)
    return jsonify({'success': True, **_overview(_uid())})


@networth_bp.route('/api/networth/snapshots', methods=['POST'])
def upsert_snapshot():
    data = request.get_json(silent=True) or {}
    try:
        nw_svc.upsert_snapshot(_uid(), data.get('date'), data.get('balances'), data.get('note', ''))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, **_overview(_uid())})


@networth_bp.route('/api/networth/snapshots/<date>', methods=['DELETE'])
def delete_snapshot(date):
    nw_svc.delete_snapshot(_uid(), date)
    return jsonify({'success': True, **_overview(_uid())})
