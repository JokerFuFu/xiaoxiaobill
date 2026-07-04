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


@analysis_bp.route('/api/time_analysis')
def time_analysis():
    """获取时间分析数据"""
    try:
        df = load_alipay_data()

        year = request.args.get('year', type=int)
        filter_type = request.args.get('filter', 'all')

        expense_df = df[(df['收/支'] == '支出') & (~df['是否退款'])]
        expense_df = expense_df[expense_df['金额'] > 0]

        if year:
            expense_df = expense_df[expense_df['交易时间'].dt.year == year]

        if filter_type == 'large':
            expense_df = expense_df[expense_df['金额'] > 1000]
        elif filter_type == 'small':
            expense_df = expense_df[expense_df['金额'] <= 1000]

        # 计算日内时段分布
        expense_df['hour'] = expense_df['交易时间'].dt.hour
        hourly_stats = expense_df.groupby('hour').agg({
            '金额': 'sum',
            '交易时间': 'count'
        }).reset_index()

        all_hours = pd.DataFrame({'hour': range(24)})
        hourly_stats = pd.merge(all_hours, hourly_stats, on='hour', how='left').fillna(0)

        hourly_data = {
            'amounts': hourly_stats['金额'].round(2).tolist(),
            'counts': hourly_stats['交易时间'].tolist()
        }

        # 计算工作日/周末分布
        expense_df['is_weekend'] = expense_df['交易时间'].dt.dayofweek.isin([5, 6])
        category_weekday = {}

        for category in expense_df['交易分类'].unique():
            category_df = expense_df[expense_df['交易分类'] == category]

            if len(category_df) == 0:
                continue

            weekday_amount = category_df[~category_df['is_weekend']]['金额'].sum()
            weekend_amount = category_df[category_df['is_weekend']]['金额'].sum()
            total_amount = weekday_amount + weekend_amount

            if total_amount == 0:
                continue

            weekday_count = len(category_df[~category_df['is_weekend']])
            weekend_count = len(category_df[category_df['is_weekend']])

            category_weekday[category] = {
                'weekday': {
                    'amount': float(weekday_amount),
                    'count': int(weekday_count),
                    'percentage': round(weekday_amount / total_amount * 100, 1)
                },
                'weekend': {
                    'amount': float(weekend_amount),
                    'count': int(weekend_count),
                    'percentage': round(weekend_amount / total_amount * 100, 1)
                }
            }

        sorted_categories = sorted(
            category_weekday.items(),
            key=lambda x: x[1]['weekday']['amount'] + x[1]['weekend']['amount'],
            reverse=True
        )
        category_weekday = dict(sorted_categories)

        return jsonify({
            'hourly': hourly_data,
            'weekday_weekend': category_weekday
        })

    except Exception as e:
        logger.error(f"Error in time analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/api/daily_data')
def daily_data():
    """获取热力图数据"""
    try:
        df = load_alipay_data()

        year = request.args.get('year', type=int)
        filter_type = request.args.get('filter', 'all')

        if filter_type == 'large':
            df = df[df['金额'] > 1000]
        elif filter_type == 'small':
            df = df[df['金额'] <= 1000]

        if year:
            df = df[df['交易时间'].dt.year == year]

        df = df[df['收/支'].isin(['收入', '支出'])]

        daily_data = df.groupby(['日期', '收/支']).agg({
            '金额': 'sum',
            '交易时间': 'count'
        }).reset_index()

        expense_data = []
        income_data = []
        transaction_data = []

        for date, group in daily_data.groupby('日期'):
            expense = group[group['收/支'] == '支出']
            if not expense.empty:
                expense_data.append([date, float(expense['金额'].iloc[0])])

            income = group[group['收/支'] == '收入']
            if not income.empty:
                income_data.append([date, float(income['金额'].iloc[0])])

            transaction_count = group['交易时间'].sum()
            transaction_data.append([date, int(transaction_count)])

        expense_amounts = [x[1] for x in expense_data]
        income_amounts = [x[1] for x in income_data]

        expense_quantiles = []
        income_quantiles = []

        if expense_amounts:
            expense_quantiles = [
                round(float(x), 2) for x in np.quantile(expense_amounts, [0.2, 0.4, 0.6, 0.8])
            ]

        if income_amounts:
            income_quantiles = [
                round(float(x), 2) for x in np.quantile(income_amounts, [0.2, 0.4, 0.6, 0.8])
            ]

        return jsonify({
            'expense': expense_data,
            'income': income_data,
            'transaction': transaction_data,
            'expense_quantiles': expense_quantiles,
            'income_quantiles': income_quantiles
        })

    except Exception as e:
        logger.error(f"Error in daily data: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============ 概览数据 API ============
