"""
对账中心 + 口径规则 API。

- GET  /api/reconcile?year=         全量对账报告(瀑布/性质明细/平台喂养/信用卡/疑似双算)
- GET  /api/nature/rules            用户自定义口径规则 + 可选性质清单
- POST /api/nature/rules            整体替换规则(保存后数据缓存自动失效,全站口径即时生效)
"""
import logging

from flask import Blueprint, abort, jsonify, request

from utils.session import get_current_uid
from services.data_loader import load_alipay_data
from services import reconcile as rec_svc
from services import nature as nature_svc

logger = logging.getLogger(__name__)
reconcile_bp = Blueprint('reconcile', __name__)


def _uid():
    uid = get_current_uid()
    if not uid:
        abort(401)   # fail-closed:不落入共享匿名空间
    return uid


@reconcile_bp.route('/api/reconcile')
def reconcile_report():
    year = request.args.get('year', type=int)
    try:
        df = load_alipay_data()
        years = sorted(df['交易时间'].dt.year.unique().tolist(), reverse=True)
    except FileNotFoundError:
        return jsonify({'success': True, 'empty': True, 'years': []})
    except Exception:
        logger.exception("对账数据加载失败")
        return jsonify({'success': True, 'empty': True, 'years': []})
    if not year and years:
        year = years[0]
    try:
        report = rec_svc.full_report(df, year)
    except Exception:
        logger.exception("对账报告生成失败")
        return jsonify({'success': False, 'error': '对账失败,请稍后重试'}), 500
    return jsonify({'success': True, 'empty': False, 'year': year, 'years': years, **report})


@reconcile_bp.route('/api/nature/rules', methods=['GET'])
def get_rules():
    return jsonify({'success': True,
                    'rules': nature_svc.load_rules(_uid()),
                    'natures': nature_svc.NATURES,
                    'fields': list(nature_svc.RULE_FIELDS)})


@reconcile_bp.route('/api/nature/rules', methods=['POST'])
def save_rules():
    data = request.get_json(silent=True) or {}
    try:
        rules = nature_svc.save_rules(_uid(), data.get('rules'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'rules': rules})
