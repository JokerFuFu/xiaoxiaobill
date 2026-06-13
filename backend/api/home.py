"""
首页概览 + 预算 API。

- GET  /api/home/overview        首页仪表盘一次拉全
- GET  /api/budget               取预算配置
- POST /api/budget               保存预算 {monthly_total, categories:{分类:额度}}
- GET  /api/budget/status        某月预算执行 {year?, month?}
"""
import logging

from flask import Blueprint, abort, jsonify, request

from utils.session import get_current_uid
from services.data_loader import load_alipay_data
from services import home as home_svc
from services import budget as budget_svc

logger = logging.getLogger(__name__)
home_bp = Blueprint('home', __name__)


def _uid():
    uid = get_current_uid()
    if not uid:
        abort(401)
    return uid


@home_bp.route('/api/home/overview')
def overview():
    try:
        df = load_alipay_data()
    except FileNotFoundError:
        return jsonify({'success': True, 'empty': True})
    except Exception:
        logger.exception("首页数据加载失败")
        return jsonify({'success': True, 'empty': True})
    try:
        data = home_svc.overview(df, _uid())
    except Exception:
        logger.exception("首页概览生成失败")
        return jsonify({'success': False, 'error': '加载失败,请稍后重试'}), 500
    return jsonify({'success': True, 'empty': False, **data})


@home_bp.route('/api/budget', methods=['GET'])
def get_budget():
    return jsonify({'success': True, 'budget': budget_svc.get_budget(_uid())})


@home_bp.route('/api/budget', methods=['POST'])
def save_budget():
    data = request.get_json(silent=True) or {}
    cats = data.get('categories')
    if cats is not None and not isinstance(cats, dict):
        return jsonify({'success': False, 'error': 'categories 须为对象'}), 400
    b = budget_svc.save_budget(_uid(), monthly_total=data.get('monthly_total'), categories=cats)
    return jsonify({'success': True, 'budget': b})


@home_bp.route('/api/budget/status')
def budget_status():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    try:
        df = load_alipay_data()
    except FileNotFoundError:
        return jsonify({'success': True, 'status': {'has_budget': False}})
    try:
        st = budget_svc.status(_uid(), df, year, month)
    except Exception:
        logger.exception("预算状态计算失败")
        return jsonify({'success': False, 'error': '计算失败'}), 500
    return jsonify({'success': True, 'status': st})
