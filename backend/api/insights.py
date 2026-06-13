"""
账单洞察 API:订阅/定期扣费、境外消费、异常提醒、年度账单报告。

- GET  /api/recurring                  订阅/定期扣费识别
- GET  /api/overseas?year=             境外消费(year 可选)
- GET  /api/anomalies                  异常消费提醒
- GET  /api/annual_report?year=        年度账单数据 + 已缓存的 AI 小结(+ai_enabled)
- POST /api/annual_report/narrative    生成/刷新年度账单 AI 小结 {year?, force?}
"""
import logging

from flask import Blueprint, abort, jsonify, request

from utils.session import get_current_uid
from services.data_loader import load_alipay_data
from services import overseas as overseas_svc
from services import recurring as recurring_svc
from services import anomaly as anomaly_svc
from services import annual_report as annual_svc
from services import ai as ai_svc

logger = logging.getLogger(__name__)
insights_bp = Blueprint('insights', __name__)


def _uid():
    uid = get_current_uid()
    if not uid:
        abort(401)
    return uid


def _df_or_empty():
    """返回 df;无数据返回 None(上层据此回空)。"""
    try:
        return load_alipay_data()
    except FileNotFoundError:
        return None
    except Exception:
        logger.exception("洞察:数据加载失败")
        return None


@insights_bp.route('/api/recurring')
def recurring():
    df = _df_or_empty()
    if df is None:
        return jsonify({'success': True, 'empty': True})
    year = request.args.get('year', type=int)
    try:
        data = recurring_svc.detect(df, year)
    except Exception:
        logger.exception("订阅识别失败")
        return jsonify({'success': False, 'error': '识别失败,请稍后重试'}), 500
    return jsonify({'success': True, 'empty': False, **data})


@insights_bp.route('/api/overseas')
def overseas():
    df = _df_or_empty()
    if df is None:
        return jsonify({'success': True, 'empty': True})
    year = request.args.get('year', type=int)
    try:
        data = overseas_svc.detect(df, year)
    except Exception:
        logger.exception("境外消费识别失败")
        return jsonify({'success': False, 'error': '识别失败,请稍后重试'}), 500
    return jsonify({'success': True, 'empty': False, **data})


@insights_bp.route('/api/anomalies')
def anomalies():
    df = _df_or_empty()
    if df is None:
        return jsonify({'success': True, 'empty': True})
    try:
        data = anomaly_svc.detect(df)
    except Exception:
        logger.exception("异常检测失败")
        return jsonify({'success': False, 'error': '检测失败,请稍后重试'}), 500
    return jsonify({'success': True, 'empty': False, **data})


@insights_bp.route('/api/annual_report')
def annual_report():
    df = _df_or_empty()
    if df is None:
        return jsonify({'success': True, 'empty': True})
    uid = _uid()
    year = request.args.get('year', type=int)
    try:
        data = annual_svc.build_data(df, uid, year)
    except Exception:
        logger.exception("年度账单生成失败")
        return jsonify({'success': False, 'error': '生成失败,请稍后重试'}), 500
    narrative = None
    if not data.get('empty'):
        cached = annual_svc.get_cached_narrative(uid, data['year'])
        if cached:
            narrative = cached
    ai_enabled = bool(ai_svc.get_ai_config(uid, 'analysis').get('api_key'))
    return jsonify({'success': True, 'data': data, 'narrative': narrative, 'ai_enabled': ai_enabled})


@insights_bp.route('/api/annual_report/narrative', methods=['POST'])
def annual_narrative():
    df = _df_or_empty()
    if df is None:
        return jsonify({'success': False, 'error': '没有账单数据'}), 400
    body = request.get_json(silent=True) or {}
    year = body.get('year')
    force = bool(body.get('force'))
    try:
        rec = annual_svc.narrative(_uid(), df, year, force=force)
    except (ValueError, RuntimeError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception:
        logger.exception("年度账单 AI 小结失败")
        return jsonify({'success': False, 'error': '生成失败,请稍后重试'}), 500
    return jsonify({'success': True, 'narrative': rec})
