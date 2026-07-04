"""api/analysis 子模块 —— 路由挂在共享的 analysis_bp 上,URL 与端点名保持不变。"""
import calendar
from datetime import datetime
from flask import jsonify, request
import pandas as pd
import numpy as np
import logging

from config import LOG_FILE, DEFAULT_PAGE, DEFAULT_PER_PAGE, MAX_PER_PAGE
from services.data_loader import load_alipay_data
from services.analysis import (
    analyze_merchants, analyze_scenarios, analyze_habits, analyze_latte_factor,
    analyze_nighttime_spending, analyze_subscriptions, analyze_inflation,
    analyze_brand_loyalty, analyze_sankey, analyze_engel_coefficient,
    analyze_weekend_vs_monday, analyze_payment_methods, analyze_bank_cards,
    analyze_members, analyze_channels, _build_channel_metas, generate_smart_tags,
    generate_story_data, calculate_monthly_stats, calculate_yearly_stats,
    calculate_change_rate,
)
from services.generators import (
    generate_chord_data, generate_funnel_data, generate_quadrant_data,
    generate_radar_data, generate_wordcloud_data, generate_themeriver_data,
    generate_boxplot_data, generate_heatmap_data, generate_pareto_data,
)

logger = logging.getLogger(__name__)

from . import analysis_bp  # noqa: E402  蓝图在 __init__ 中先于本模块导入而定义
from ._helpers import _member_analysis_with_colors  # noqa: E402


@analysis_bp.route('/api/member_analysis')
def member_analysis():
    """成员维度独立接口(供成员对比卡片)。"""
    try:
        df = load_alipay_data()
        year = request.args.get('year', type=int)
        if year:
            df = df[df['交易时间'].dt.year == year]
        return jsonify({'success': True, 'members': _member_analysis_with_colors(df)})
    except FileNotFoundError:
        return jsonify({'success': True, 'members': []})
    except Exception as e:
        logger.error(f"member_analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 综合分析结果缓存(消费洞察页很重,~20 项分析)。键含数据签名,文件变即失效。
_analysis_result_cache = {}
_ANALYSIS_CACHE_MAX = 16


@analysis_bp.route('/api/channel_analysis')
def channel_analysis():
    """渠道分析：银行卡（储蓄/信用·按卡号）/支付宝/微信 多维统计。"""
    try:
        df = load_alipay_data()

        year = request.args.get('year', type=int)
        if year:
            df = df[df['交易时间'].dt.year == year]

        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        if min_amount:
            df = df[df['金额'] >= min_amount]
        if max_amount:
            df = df[df['金额'] <= max_amount]

        return jsonify({'success': True, 'data': analyze_channels(df)})

    except Exception as e:
        logger.error(f"渠道分析出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f'渠道分析失败: {str(e)}'}), 500
