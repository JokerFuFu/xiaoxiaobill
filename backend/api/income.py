"""
收入分析 API。

- GET /api/income_analysis?year=   薪资/理财收益/其他收入 全量报告
"""
import logging

from flask import Blueprint, jsonify, request

from services.data_loader import load_alipay_data
from services import income as income_svc

logger = logging.getLogger(__name__)
income_bp = Blueprint('income', __name__)


@income_bp.route('/api/income_analysis')
def income_analysis():
    year = request.args.get('year', type=int)
    try:
        df = load_alipay_data()
        years = sorted(df['交易时间'].dt.year.unique().tolist(), reverse=True)
    except FileNotFoundError:
        return jsonify({'success': True, 'empty': True, 'years': []})
    except Exception:
        logger.exception("收入分析数据加载失败")
        return jsonify({'success': True, 'empty': True, 'years': []})
    if not year and years:
        year = years[0]
    try:
        report = income_svc.full_report(df, year)
    except Exception:
        logger.exception("收入分析生成失败")
        return jsonify({'success': False, 'error': '收入分析失败,请稍后重试'}), 500
    return jsonify({'success': True, 'empty': False, 'year': year, 'years': years, **report})
