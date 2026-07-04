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


@analysis_bp.route('/api/yearly_analysis')
def yearly_analysis():
    """年度分析 API"""
    try:
        df = load_alipay_data()
        year = request.args.get('year', type=int)
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)

        # 获取当前年份数据
        current_year_df = df[df['交易时间'].dt.year == year] if year else df

        # 获取上一年数据
        last_year = year - 1 if year else df['交易时间'].dt.year.max() - 1
        last_year_df = df[df['交易时间'].dt.year == last_year]

        # 应用金额筛选
        if min_amount:
            current_year_df = current_year_df[current_year_df['金额'] >= min_amount]
            last_year_df = last_year_df[last_year_df['金额'] >= min_amount]
        if max_amount:
            current_year_df = current_year_df[current_year_df['金额'] < max_amount]
            last_year_df = last_year_df[last_year_df['金额'] < max_amount]

        # 过滤有效交易
        current_expense_df = current_year_df[
            (current_year_df['收/支'] == '支出') &
            (~current_year_df['是否退款'])
        ]
        current_income_df = current_year_df[
            (current_year_df['收/支'] == '收入') &
            (~current_year_df['是否退款'])
        ]

        last_expense_df = last_year_df[
            (last_year_df['收/支'] == '支出') &
            (~last_year_df['是否退款'])
        ]
        last_income_df = last_year_df[
            (last_year_df['收/支'] == '收入') &
            (~last_year_df['是否退款'])
        ]

        # 计算当前年份数据
        current_expense = current_expense_df['金额'].sum()
        current_income = current_income_df['金额'].sum()
        current_balance = current_income - current_expense

        # 计算上一年数据
        last_expense = last_expense_df['金额'].sum()
        last_income = last_income_df['金额'].sum()
        last_balance = last_income - last_expense

        # 生成完整的月份列表
        all_months = [f"{year}-{str(month).zfill(2)}" for month in range(1, 13)]

        # 按月统计支出和收入
        monthly_expenses = current_expense_df.groupby(
            current_expense_df['交易时间'].dt.strftime('%Y-%m')
        )['金额'].sum()
        monthly_incomes = current_income_df.groupby(
            current_income_df['交易时间'].dt.strftime('%Y-%m')
        )['金额'].sum()

        monthly_expenses = monthly_expenses.reindex(all_months, fill_value=0)
        monthly_incomes = monthly_incomes.reindex(all_months, fill_value=0)

        # 计算分类统计
        category_expenses = current_expense_df.groupby('交易分类')['金额'].sum()
        category_incomes = current_income_df.groupby('交易分类')['金额'].sum()

        # 计算分来源的分类统计
        expense_source = current_expense_df.groupby(['来源', '交易分类'])['金额'].sum().reset_index().to_dict('records')
        income_source = current_income_df.groupby(['来源', '交易分类'])['金额'].sum().reset_index().to_dict('records')

        # 计算年度统计数据
        yearly_stats = {
            'balance': float(current_balance),
            'total_expense': float(current_expense),
            'total_income': float(current_income),
            'expense_count': int(len(current_expense_df)),
            'income_count': int(len(current_income_df)),
            'total_count': int(len(current_expense_df) + len(current_income_df)),
            'active_days': int(len(current_year_df['交易时间'].dt.date.unique())),
            'avg_transaction': float(current_expense_df['金额'].mean()) if len(current_expense_df) > 0 else 0,
            'avg_daily_expense': float(current_expense / max(1, len(current_year_df['交易时间'].dt.date.unique()))),
            'avg_monthly_income': float(current_income / 12),
            'expense_ratio': float(current_expense / current_income * 100) if current_income > 0 else 0,
            'comparisons': {
                'balance': {
                    'change': float(current_balance - last_balance) if len(last_year_df) > 0 else None,
                    'rate': float((current_balance - last_balance) / abs(last_balance) * 100) if len(last_year_df) > 0 and last_balance != 0 else None
                },
                'expense': {
                    'change': float(current_expense - last_expense) if len(last_year_df) > 0 else None,
                    'rate': float((current_expense - last_expense) / last_expense * 100) if len(last_year_df) > 0 and last_expense != 0 else None
                },
                'income': {
                    'change': float(current_income - last_income) if len(last_year_df) > 0 else None,
                    'rate': float((current_income - last_income) / last_income * 100) if len(last_year_df) > 0 and last_income != 0 else None
                },
                'count': {
                    'change': int(len(current_expense_df) + len(current_income_df) - len(last_expense_df) - len(last_income_df)) if len(last_year_df) > 0 else None,
                    'rate': float((len(current_expense_df) + len(current_income_df) - len(last_expense_df) - len(last_income_df)) / (len(last_expense_df) + len(last_income_df)) * 100) if len(last_year_df) > 0 and (len(last_expense_df) + len(last_income_df)) != 0 else None
                }
            }
        }

        logger.info(f"Yearly stats: income={current_income}, expense={current_expense}, balance={current_balance}")

        return jsonify({
            'success': True,
            'data': {
                'trends': {
                    'months': monthly_expenses.index.tolist(),
                    'expenses': monthly_expenses.values.tolist(),
                    'incomes': monthly_incomes.values.tolist()
                },
                'categories': {
                    'expense': {
                        'names': category_expenses.index.tolist(),
                        'amounts': category_expenses.values.tolist()
                    },
                    'income': {
                        'names': category_incomes.index.tolist(),
                        'amounts': category_incomes.values.tolist()
                    }
                },
                'categories_source': {
                    'expense': expense_source,
                    'income': income_source
                },
                'yearly_stats': yearly_stats
            }
        })

    except Exception as e:
        logger.error(f"Error in yearly analysis: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@analysis_bp.route('/api/yearly_data')
def yearly_data():
    """获取年度数据"""
    try:
        df = load_alipay_data()
        logger.info(f"数据加载完成，总行数: {len(df)}")

        available_years = sorted(df['交易时间'].dt.year.unique().tolist(), reverse=True)

        year = request.args.get('year', available_years[0], type=int)
        logger.info(f"请求年度数据: {year}")

        current_year_df = df[df['交易时间'].dt.year == year].copy()
        logger.info(f"当前年份数据行数: {len(current_year_df)}")

        last_year_df = df[df['交易时间'].dt.year == (year - 1)].copy()
        logger.info(f"上一年数据行数: {len(last_year_df)}")

        filter_type = request.args.get('filter', 'all')

        if filter_type == 'large':
            current_year_df = current_year_df[current_year_df['金额'] >= 1000]
            last_year_df = last_year_df[last_year_df['金额'] >= 1000] if not last_year_df.empty else last_year_df
        elif filter_type == 'small':
            current_year_df = current_year_df[current_year_df['金额'] < 1000]
            last_year_df = last_year_df[last_year_df['金额'] < 1000] if not last_year_df.empty else last_year_df

        current_stats = calculate_yearly_stats(current_year_df)

        yearly_stats = {
            **current_stats,
        }

        if len(last_year_df) > 0:
            last_year_stats = calculate_yearly_stats(last_year_df)

            balance_change_rate = calculate_change_rate(current_stats['balance'], last_year_stats['balance'])
            expense_change_rate = calculate_change_rate(current_stats['total_expense'], last_year_stats['total_expense'])
            income_change_rate = calculate_change_rate(current_stats['total_income'], last_year_stats['total_income'])
            transaction_change_rate = calculate_change_rate(current_stats['total_count'], last_year_stats['total_count'])

            yearly_stats.update({
                'balance_change': float(current_stats['balance'] - last_year_stats['balance']),
                'expense_change': float(current_stats['total_expense'] - last_year_stats['total_expense']),
                'income_change': float(current_stats['total_income'] - last_year_stats['total_income']),
                'transaction_change': int(current_stats['total_count'] - last_year_stats['total_count']),
                'balance_change_rate': float(balance_change_rate) if balance_change_rate is not None else None,
                'expense_change_rate': float(expense_change_rate) if expense_change_rate is not None else None,
                'income_change_rate': float(income_change_rate) if income_change_rate is not None else None,
                'transaction_change_rate': float(transaction_change_rate) if transaction_change_rate is not None else None
            })
        else:
            yearly_stats.update({
                'balance_change': None,
                'expense_change': None,
                'income_change': None,
                'transaction_change': None,
                'balance_change_rate': None,
                'expense_change_rate': None,
                'income_change_rate': None,
                'transaction_change_rate': None
            })

        months = sorted(current_year_df['月份'].unique().tolist())
        expenses = []
        incomes = []

        for month in months:
            month_data = current_year_df[current_year_df['月份'] == month]
            expenses.append(float(round(month_data[
                (month_data['收/支'] == '支出') &
                (~month_data['是否退款'])
            ]['金额'].sum(), 2)))
            incomes.append(float(round(month_data[
                (month_data['收/支'] == '收入') &
                (~month_data['是否退款'])
            ]['金额'].sum(), 2)))

        expense_df = current_year_df[
            (current_year_df['收/支'] == '支出') &
            (~current_year_df['是否退款'])
        ]
        categories = expense_df.groupby('交易分类')['金额'].sum().sort_values(ascending=False)

        return jsonify({
            'yearly_stats': yearly_stats,
            'months': months,
            'expenses': expenses,
            'incomes': incomes,
            'categories': categories.index.tolist(),
            'amounts_by_category': [float(x) for x in categories.values.tolist()],
            'available_years': available_years,
            'current_year': int(year)
        })

    except Exception as e:
        logger.error(f"处理年度数据时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============ 月度分析 API ============
