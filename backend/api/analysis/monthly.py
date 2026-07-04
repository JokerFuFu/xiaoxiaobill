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


@analysis_bp.route('/api/monthly_analysis')
def monthly_analysis():
    """月度分析 API"""
    try:
        df = load_alipay_data()
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)

        # 获取当前月份数据
        current_month_df = df[
            (df['交易时间'].dt.year == year) &
            (df['交易时间'].dt.month == month)
        ]

        # 获取上月数据
        last_month = month - 1 if month > 1 else 12
        last_year = year if month > 1 else year - 1
        last_month_df = df[
            (df['交易时间'].dt.year == last_year) &
            (df['交易时间'].dt.month == last_month)
        ]

        # 应用金额筛选
        if min_amount:
            current_month_df = current_month_df[current_month_df['金额'] >= min_amount]
            last_month_df = last_month_df[last_month_df['金额'] >= min_amount]
        if max_amount:
            current_month_df = current_month_df[current_month_df['金额'] < max_amount]
            last_month_df = last_month_df[last_month_df['金额'] < max_amount]

        # 处理收入和支出数据
        current_expense_df = current_month_df[
            (current_month_df['收/支'] == '支出') &
            (~current_month_df['是否退款'])
        ]
        current_income_df = current_month_df[
            (current_month_df['收/支'] == '收入') &
            (~current_month_df['是否退款'])
        ]

        # 计算统计数据
        current_expense = current_expense_df['金额'].sum()
        current_income = current_income_df['金额'].sum()
        current_balance = current_income - current_expense

        # 计算上月数据
        last_expense = last_month_df[
            (last_month_df['收/支'] == '支出') &
            (~last_month_df['是否退款'])
        ]['金额'].sum()
        last_income = last_month_df[
            (last_month_df['收/支'] == '收入') &
            (~last_month_df['是否退款'])
        ]['金额'].sum()
        last_balance = last_income - last_expense

        # 按日期统计
        daily_expenses = current_expense_df.groupby(
            current_expense_df['交易时间'].dt.date
        )['金额'].sum()
        daily_incomes = current_income_df.groupby(
            current_income_df['交易时间'].dt.date
        )['金额'].sum()

        # 计算分类统计
        expense_categories = current_expense_df.groupby('交易分类')['金额'].sum()
        income_categories = current_income_df.groupby('交易分类')['金额'].sum()

        # 计算分来源的分类统计
        expense_source = current_expense_df.groupby(['来源', '交易分类'])['金额'].sum().reset_index().to_dict('records')
        income_source = current_income_df.groupby(['来源', '交易分类'])['金额'].sum().reset_index().to_dict('records')

        # 生成当月所有日期
        last_day = calendar.monthrange(year, month)[1]
        all_dates = [
            datetime(year, month, day).date()
            for day in range(1, last_day + 1)
        ]

        # 补充所有日期，缺失的填充0
        daily_expenses = daily_expenses.reindex(all_dates, fill_value=0)
        daily_incomes = daily_incomes.reindex(all_dates, fill_value=0)

        return jsonify({
            'success': True,
            'data': {
                'stats': {
                    'balance': float(current_balance),
                    'total_expense': float(current_expense),
                    'total_income': float(current_income),
                    'expense_count': int(len(current_expense_df)),
                    'income_count': int(len(current_income_df)),
                    'comparisons': {
                        'balance': {
                            'change': float(current_balance - last_balance),
                            'rate': float((current_balance - last_balance) / abs(last_balance) * 100) if last_balance != 0 else None
                        },
                        'expense': {
                            'change': float(current_expense - last_expense),
                            'rate': float((current_expense - last_expense) / last_expense * 100) if last_expense != 0 else None
                        },
                        'income': {
                            'change': float(current_income - last_income),
                            'rate': float((current_income - last_income) / last_income * 100) if last_income != 0 else None
                        }
                    }
                },
                'daily_data': {
                    'expense': {
                        'dates': [d.strftime('%Y-%m-%d') for d in all_dates],
                        'amounts': daily_expenses.values.tolist()
                    },
                    'income': {
                        'dates': [d.strftime('%Y-%m-%d') for d in all_dates],
                        'amounts': daily_incomes.values.tolist()
                    }
                },
                'categories': {
                    'expense': {
                        'names': expense_categories.index.tolist(),
                        'amounts': expense_categories.values.tolist()
                    },
                    'income': {
                        'names': income_categories.index.tolist(),
                        'amounts': income_categories.values.tolist()
                    }
                },
                'categories_source': {
                    'expense': expense_source,
                    'income': income_source
                }
            }
        })

    except Exception as e:
        logger.error(f"Error in monthly analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@analysis_bp.route('/api/monthly_data')
def get_monthly_data():
    """获取月度数据"""
    try:
        df = load_alipay_data()

        available_months = sorted(df['月份'].unique().tolist(), reverse=True)

        latest_month = available_months[0]
        default_year = int(latest_month.split('-')[0])
        default_month = int(latest_month.split('-')[1])

        current_year = request.args.get('year', default_year, type=int)
        current_month = request.args.get('month', default_month, type=int)

        logger.info(f"请求月度数据: {current_year}-{current_month}")

        current_month_str = f"{current_year}-{current_month:02d}"
        current_month_df = df[df['月份'] == current_month_str].copy()

        if current_month == 1:
            last_month_year = current_year - 1
            last_month = 12
        else:
            last_month_year = current_year
            last_month = current_month - 1

        last_month_str = f"{last_month_year}-{last_month:02d}"
        last_month_df = df[df['月份'] == last_month_str].copy()

        filter_type = request.args.get('filter', 'all')

        if filter_type == 'large':
            current_month_df = current_month_df[current_month_df['金额'] >= 1000]
            last_month_df = last_month_df[last_month_df['金额'] >= 1000] if not last_month_df.empty else last_month_df
        elif filter_type == 'small':
            current_month_df = current_month_df[current_month_df['金额'] < 1000]
            last_month_df = last_month_df[last_month_df['金额'] < 1000] if not last_month_df.empty else last_month_df

        current_stats = calculate_monthly_stats(current_month_df)
        monthly_stats = {
            **current_stats,
        }

        if not last_month_df.empty:
            last_stats = calculate_monthly_stats(last_month_df)

            comparisons = {}
            for key in ['total_expense', 'total_income', 'balance']:
                current_val = current_stats[key]
                last_val = last_stats[key]
                diff = current_val - last_val
                rate = (diff / abs(last_val) * 100) if last_val != 0 else 0
                comparisons[key] = {
                    'diff': diff,
                    'rate': rate
                }
            monthly_stats['comparisons'] = comparisons

        return jsonify({
            'success': True,
            'data': monthly_stats
        })

    except Exception as e:
        logger.error(f"Error in monthly analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@analysis_bp.route('/api/filtered_monthly_analysis')
def filtered_monthly_analysis():
    """获取过滤后的月度分析"""
    df = load_alipay_data()
    filter_type = request.args.get('filter', 'all')

    expense_df = df[(df['收/支'] == '支出') & (~df['是否退款'])]
    expense_df = expense_df[expense_df['金额'] > 0]

    if filter_type == 'large':
        expense_df = expense_df[expense_df['金额'] > 1000]
    elif filter_type == 'small':
        expense_df = expense_df[expense_df['金额'] <= 1000]

    monthly_stats = expense_df.groupby('月份').agg({
        '金额': ['sum', 'count', 'mean'],
        '交易时间': lambda x: len(x.dt.date.unique())
    }).round(2)

    monthly_stats.columns = ['total', 'count', 'avg_amount', 'active_days']

    monthly_stats['daily_avg'] = (monthly_stats['total'] / monthly_stats['active_days']).round(2)
    monthly_stats['mom_rate'] = (monthly_stats['total'].pct_change() * 100).round(2)
    monthly_stats['moving_avg'] = monthly_stats['total'].rolling(3, min_periods=1).mean().round(2)

    category_expenses = expense_df.pivot_table(
        index='月份',
        columns='交易分类',
        values='金额',
        aggfunc='sum',
        fill_value=0
    )

    return jsonify({
        'months': monthly_stats.index.tolist(),
        'total_expenses': monthly_stats['total'].tolist(),
        'transaction_counts': monthly_stats['count'].tolist(),
        'daily_averages': monthly_stats['daily_avg'].tolist(),
        'mom_rates': monthly_stats['mom_rate'].fillna(0).tolist(),
        'moving_averages': monthly_stats['moving_avg'].tolist(),
        'categories': category_expenses.columns.tolist(),
        'category_expenses': category_expenses.values.tolist()
    })


# ============ 分类分析 API ============
