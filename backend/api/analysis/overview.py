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


@analysis_bp.route('/api/analysis')
def get_analysis():
    """综合分析 API"""
    try:
        from services import data_loader as _dl
        from utils.session import get_current_uid

        year = request.args.get('year', type=int)
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)

        sig = _dl.current_data_signature()
        ckey = (get_current_uid() or '__anon__', sig, year, min_amount, max_amount)
        if sig is not None and ckey in _analysis_result_cache:
            return jsonify({'success': True, 'data': _analysis_result_cache[ckey]})

        df = load_alipay_data()
        if year:
            df = df[df['交易时间'].dt.year == year]
        if min_amount:
            df = df[df['金额'] >= min_amount]
        if max_amount:
            df = df[df['金额'] < max_amount]

        data = {
                'merchant_analysis': analyze_merchants(df),
                'scenario_analysis': analyze_scenarios(df),
                'habit_analysis': analyze_habits(df),
                'latte_factor': analyze_latte_factor(df),
                'nighttime_analysis': analyze_nighttime_spending(df),
                'subscription_analysis': analyze_subscriptions(df),
                'inflation_analysis': analyze_inflation(df),
                'brand_loyalty': analyze_brand_loyalty(df),
                'sankey_data': analyze_sankey(df),
                'engel_coefficient': analyze_engel_coefficient(df),
                'weekend_monday': analyze_weekend_vs_monday(df),
                'story_data': generate_story_data(df),
                'tags': generate_smart_tags(df),
                'payment_analysis': analyze_payment_methods(df),
                'bank_card_analysis': analyze_bank_cards(df),
                'member_analysis': _member_analysis_with_colors(df),
                'chord_data': generate_chord_data(df),
                'funnel_data': generate_funnel_data(df),
                'quadrant_data': generate_quadrant_data(df),
                'radar_data': generate_radar_data(df),
                'wordcloud_data': generate_wordcloud_data(df),
                'themeriver_data': generate_themeriver_data(df),
                'boxplot_data': generate_boxplot_data(df),
                'heatmap_data': generate_heatmap_data(df),
                'pareto_data': generate_pareto_data(df)
        }

        if sig is not None:
            _analysis_result_cache[ckey] = data
            if len(_analysis_result_cache) > _ANALYSIS_CACHE_MAX:
                _analysis_result_cache.pop(next(iter(_analysis_result_cache)))
        return jsonify({'success': True, 'data': data})

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


# ============ 年度分析 API ============


@analysis_bp.route('/api/categories')
def get_categories():
    """获取所有交易分类"""
    try:
        df = load_alipay_data()
        categories = sorted(df['交易分类'].dropna().unique().tolist())
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analysis_bp.route('/api/category_available_dates')
def get_category_available_dates():
    """获取分类页面的可用日期"""
    try:
        df = load_alipay_data()

        dates = pd.DataFrame({
            'year': df['交易时间'].dt.year,
            'month': df['交易时间'].dt.month
        })

        available_months = {}
        for year in sorted(dates['year'].unique(), reverse=True):
            months = sorted(dates[dates['year'] == year]['month'].unique())
            available_months[int(year)] = [int(m) for m in months]

        return jsonify({
            'years': sorted(dates['year'].unique().tolist(), reverse=True),
            'months': available_months
        })
    except Exception as e:
        logger.error(f"Error getting category available dates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


# ============ 交易记录 API ============


@analysis_bp.route('/api/overview_data')
def get_overview_data():
    """获取概览数据"""
    try:
        df = load_alipay_data()

        filter_type = request.args.get('filter', 'all')
        year = request.args.get('year', None)

        if year is None:
            year = str(df['交易时间'].max().year)

        year_df = df[df['交易时间'].dt.year == int(year)]

        if filter_type == 'large':
            year_df = year_df[year_df['金额'].abs() >= 1000]
        elif filter_type == 'small':
            year_df = year_df[year_df['金额'].abs() < 1000]

        available_years = sorted(df['交易时间'].dt.year.unique().tolist(), reverse=True)

        expense_df = year_df[
            (year_df['收/支'] == '支出') &
            (~year_df['是否退款'])
        ]
        income_df = year_df[
            (year_df['收/支'] == '收入') &
            (~year_df['是否退款'])
        ]

        yearly_stats = {
            'total_expense': round(expense_df['金额'].sum(), 2),
            'total_income': round(income_df['金额'].sum(), 2),
            'balance': round(income_df['金额'].sum() - expense_df['金额'].sum(), 2),
            'expense_count': len(expense_df),
            'income_count': len(income_df),
            'total_count': len(expense_df) + len(income_df),
            'active_days': len(year_df['日期'].unique()),
            'avg_transaction': round(expense_df['金额'].mean(), 2) if len(expense_df) > 0 else 0,
            'avg_daily_expense': round(expense_df['金额'].sum() / 365, 2),
            'avg_monthly_income': round(income_df['金额'].sum() / 12, 2),
            'expense_ratio': round(expense_df['金额'].sum() / income_df['金额'].sum() * 100, 2) if income_df['金额'].sum() > 0 else 0
        }

        all_months = [f'{year}-{str(month).zfill(2)}' for month in range(1, 13)]

        monthly_data = expense_df.groupby('月份')['金额'].sum().round(2)

        monthly_stats = pd.DataFrame(index=all_months)
        monthly_stats['total'] = monthly_data
        monthly_stats = monthly_stats.fillna(0)

        category_stats = expense_df.groupby('交易分类')['金额'].sum().round(2).sort_values(ascending=False)

        return jsonify({
            'available_years': available_years,
            'current_year': year,
            'yearly_stats': yearly_stats,
            'months': all_months,
            'amounts': monthly_stats['total'].tolist(),
            'categories': category_stats.index.tolist(),
            'amounts_by_category': category_stats.values.tolist()
        })

    except Exception as e:
        logger.error(f"API错误: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/api/summary')
def summary():
    """获取汇总数据"""
    df = load_alipay_data()

    current_date = datetime.now()
    current_month = current_date.strftime('%Y-%m')

    expense_df = df[df['收/支'] == '支出']
    total_expense = expense_df['金额'].sum()
    total_income = df[df['收/支'] == '收入']['金额'].sum()

    monthly_expenses = expense_df.groupby('月份')['金额'].sum()

    latest_month = monthly_expenses.index[-1]
    latest_month_expense = monthly_expenses[latest_month]

    current_month_expense = monthly_expenses.get(current_month)

    display_month = current_month if current_month_expense is not None else latest_month
    display_expense = current_month_expense if current_month_expense is not None else latest_month_expense

    if len(monthly_expenses) > 1:
        prev_month_expense = monthly_expenses.iloc[-2]
    else:
        prev_month_expense = display_expense

    return jsonify({
        'total_expense': round(total_expense, 2),
        'total_income': round(total_income, 2),
        'balance': round(total_income - total_expense, 2),
        'monthly_avg': round(monthly_expenses.mean(), 2),
        'current_month_expense': round(display_expense, 2),
        'prev_monthly_avg': round(prev_month_expense, 2),
        'month_count': len(monthly_expenses),
        'transaction_count': len(expense_df),
        'current_month': display_month,
        'has_current_month_data': current_month_expense is not None
    })


# ============ 辅助接口 API ============


@analysis_bp.route('/api/available_dates')
def get_available_dates():
    """获取可用的日期列表"""
    try:
        df = load_alipay_data()
        dates = df['交易时间'].dt.strftime('%Y-%m').unique().tolist()
        dates.sort(reverse=True)

        return jsonify({
            'success': True,
            'months': dates,
            'years': sorted(df['交易时间'].dt.year.unique().tolist(), reverse=True)
        })
    except Exception as e:
        logger.error(f"Error getting available dates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@analysis_bp.route('/api/available_years')
def get_available_years():
    """获取数据中所有可用的年份"""
    try:
        df = load_alipay_data()
        years = sorted(df['交易时间'].dt.year.unique().tolist(), reverse=True)

        return jsonify({
            'success': True,
            'years': years
        })

    except Exception as e:
        logger.error(f"获取可用年份时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取可用年份失败: {str(e)}'
        }), 500
