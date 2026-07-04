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


@analysis_bp.route('/api/category_expenses')
def category_expenses():
    """获取分类支出统计"""
    df = load_alipay_data()

    category_stats = df[df['收/支'] == '支出'].groupby('交易分类').agg({
        '金额': 'sum'
    }).sort_values('金额', ascending=False)

    return jsonify({
        'categories': category_stats.index.tolist(),
        'amounts': category_stats['金额'].tolist()
    })


@analysis_bp.route('/api/category_analysis')
def category_analysis():
    """分类分析 API"""
    try:
        df = load_alipay_data()
        category = request.args.get('category')
        time_range = request.args.get('range', 'year')
        year = request.args.get('year')
        month = request.args.get('month')
        min_amount = request.args.get('min_amount')
        max_amount = request.args.get('max_amount')

        expense_df = df[
            (df['收/支'] == '支出') &
            (~df['是否退款'])
        ]

        if time_range == 'year' and year:
            expense_df = expense_df[expense_df['交易时间'].dt.year == int(year)]
        elif time_range == 'month' and year and month:
            expense_df = expense_df[
                (expense_df['交易时间'].dt.year == int(year)) &
                (expense_df['交易时间'].dt.month == int(month))
            ]

        try:
            if min_amount:
                min_val = float(min_amount)
                expense_df = expense_df[expense_df['金额'] >= min_val]
            if max_amount and max_amount.lower() != 'infinity':
                max_val = float(max_amount)
                expense_df = expense_df[expense_df['金额'] < max_val]
        except ValueError as e:
            logger.warning(f"金额转换错误: {str(e)}")

        if not category:
            categories_stats = expense_df.groupby('交易分类').agg({
                '金额': ['sum', 'count', 'mean']
            }).round(2)

            categories_stats.columns = ['total', 'count', 'avg']

            categories_stats['amount_rank'] = categories_stats['total'].rank(ascending=False)
            categories_stats['count_rank'] = categories_stats['count'].rank(ascending=False)
            categories_stats['score'] = 0.7 * categories_stats['amount_rank'] + 0.3 * categories_stats['count_rank']

            categories_stats = categories_stats.sort_values('score', ascending=True)

            category_groups = None
            if '来源' in expense_df.columns:
                global_order = categories_stats['score'].sort_values(ascending=True).index.tolist()

                alipay_existing = expense_df[expense_df['来源'] == '支付宝']['交易分类'].unique()
                wechat_existing = expense_df[expense_df['来源'] == '微信']['交易分类'].unique()

                alipay_cats = [cat for cat in global_order if cat in alipay_existing]
                wechat_cats = [cat for cat in global_order if cat in wechat_existing]

                alipay_set = set(alipay_cats)
                wechat_cats = [c for c in wechat_cats if c not in alipay_set]

                category_groups = {
                    'alipay': alipay_cats,
                    'wechat': wechat_cats
                }

            return jsonify({
                'categories': categories_stats.index.tolist(),
                'category_groups': category_groups,
                'stats': {
                    'totals': categories_stats['total'].tolist(),
                    'counts': categories_stats['count'].tolist(),
                    'averages': categories_stats['avg'].tolist()
                }
            })

        category_df = expense_df[expense_df['交易分类'] == category]

        if category_df.empty:
            return jsonify({
                'error': f'未找到分类 "{category}" 的数据'
            }), 404

        if time_range == 'all':
            date_range = (category_df['交易时间'].max() - category_df['交易时间'].min()).days + 1
        elif time_range == 'year':
            date_range = 365
        else:
            date_range = calendar.monthrange(int(year), int(month))[1]

        total_expense = category_df['金额'].sum()
        transaction_count = len(category_df)
        avg_amount = round(category_df['金额'].mean(), 2) if transaction_count > 0 else 0

        if time_range == 'all':
            total_all_expense = expense_df['金额'].sum()
        elif time_range == 'year':
            total_all_expense = expense_df[expense_df['交易时间'].dt.year == int(year)]['金额'].sum()
        else:
            total_all_expense = expense_df[
                (expense_df['交易时间'].dt.year == int(year)) &
                (expense_df['交易时间'].dt.month == int(month))
            ]['金额'].sum()

        expense_ratio = round((total_expense / total_all_expense * 100), 2) if total_all_expense > 0 else 0

        if time_range == 'all':
            grouped = category_df.groupby(category_df['交易时间'].dt.strftime('%Y'))
            total_grouped = expense_df.groupby(expense_df['交易时间'].dt.strftime('%Y'))
        elif time_range == 'year':
            grouped = category_df.groupby(category_df['交易时间'].dt.strftime('%Y-%m'))
            total_grouped = expense_df.groupby(expense_df['交易时间'].dt.strftime('%Y-%m'))
        else:
            grouped = category_df.groupby(category_df['交易时间'].dt.strftime('%Y-%m-%d'))
            total_grouped = expense_df.groupby(expense_df['交易时间'].dt.strftime('%Y-%m-%d'))

        time_series = grouped['金额'].sum().round(2)
        total_series = total_grouped['金额'].sum().round(2)
        transaction_counts = grouped.size()

        ratios = []
        for date in time_series.index:
            if date in total_series.index and total_series[date] > 0:
                ratio = (time_series[date] / total_series[date] * 100).round(1)
            else:
                ratio = 0
            ratios.append(ratio)

        full_time_series = time_series.copy()
        full_transaction_counts = transaction_counts.copy()
        full_ratios = []

        if time_range == 'year':
            full_index = pd.period_range(start=f'{year}-01', end=f'{year}-12', freq='M').strftime('%Y-%m')
            full_time_series = time_series.reindex(full_index, fill_value=0)
            full_transaction_counts = transaction_counts.reindex(full_index, fill_value=0)
            full_total_series = total_series.reindex(full_index, fill_value=0)

            for date in full_time_series.index:
                if full_total_series[date] > 0:
                    ratio = (full_time_series[date] / full_total_series[date] * 100).round(1)
                else:
                    ratio = 0
                full_ratios.append(ratio)

        elif time_range == 'month':
            days_in_month = calendar.monthrange(int(year), int(month))[1]
            full_index = pd.period_range(start=f'{year}-{month}-01', periods=days_in_month, freq='D').strftime('%Y-%m-%d')
            full_time_series = time_series.reindex(full_index, fill_value=0)
            full_transaction_counts = transaction_counts.reindex(full_index, fill_value=0)
            full_total_series = total_series.reindex(full_index, fill_value=0)

            for date in full_time_series.index:
                if full_total_series[date] > 0:
                    ratio = (full_time_series[date] / full_total_series[date] * 100).round(1)
                else:
                    ratio = 0
                full_ratios.append(ratio)
        else:
            full_time_series = time_series
            full_transaction_counts = transaction_counts
            full_ratios = ratios

        hour_pattern = category_df.groupby(category_df['交易时间'].dt.hour)['金额'].agg([
            ('count', 'count'),
            ('sum', 'sum')
        ]).round(2)

        amount_ranges = [0, 50, 100, 200, 500, 1000, float('inf')]
        amount_labels = ['0-50', '50-100', '100-200', '200-500', '500-1000', '1000+']
        amount_dist = pd.cut(category_df['金额'], bins=amount_ranges, labels=amount_labels)
        amount_distribution = amount_dist.value_counts().sort_index()

        full_hours = pd.Index(range(24), name='交易时间')
        hour_pattern_full = hour_pattern.reindex(full_hours, fill_value=0)

        amount_distribution_full = amount_distribution.reindex(amount_labels, fill_value=0)

        return jsonify({
            'category': category,
            'stats': {
                'total_expense': float(total_expense),
                'transaction_count': int(transaction_count),
                'avg_amount': float(avg_amount),
                'expense_ratio': float(expense_ratio),
                'date_range': int(date_range),
                'max_amount': float(category_df['金额'].max()) if not category_df.empty else 0,
                'min_amount': float(category_df['金额'].min()) if not category_df.empty else 0,
                'median_amount': float(category_df['金额'].median()) if not category_df.empty else 0
            },
            'trend': {
                'dates': full_time_series.index.tolist(),
                'amounts': full_time_series.fillna(0).values.tolist(),
                'counts': full_transaction_counts.fillna(0).values.tolist(),
                'ratios': [0 if np.isnan(x) else x for x in full_ratios]
            },
            'pattern': {
                'hours': hour_pattern_full.index.tolist(),
                'counts': hour_pattern_full['count'].tolist(),
                'amounts': hour_pattern_full['sum'].tolist(),
                'averages': (hour_pattern_full['sum'] / hour_pattern_full['count']).round(2).fillna(0).tolist()
            },
            'distribution': {
                'ranges': amount_distribution_full.index.tolist(),
                'counts': amount_distribution_full.values.tolist(),
                'percentages': (amount_distribution_full / amount_distribution_full.sum() * 100).round(1).fillna(0).tolist()
            }
        })

    except Exception as e:
        logger.error(f"处理分类分析数据时出错: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/api/category_detail/<month>/<category>')
def category_detail(month, category):
    """获取指定月份和分类的支出明细"""
    df = load_alipay_data()

    details = df[
        (df['月份'] == month) &
        (df['交易分类'] == category) &
        (df['收/支'] == '支出')
    ].sort_values('金额', ascending=False)[
        ['交易时间', '商品说明', '交易对方', '金额', '交易状态']
    ].to_dict('records')

    formatted_details = [{
        'time': detail['交易时间'].strftime('%Y-%m-%d %H:%M:%S'),
        'description': detail['商品说明'],
        'counterparty': detail['交易对方'],
        'amount': round(float(detail['金额']), 2),
        'status': detail['交易状态']
    } for detail in details]

    return jsonify(formatted_details)


@analysis_bp.route('/api/category_trend/<category>')
def category_trend(category):
    """获取指定分类的月度趋势"""
    df = load_alipay_data()

    category_df = df[
        (df['收/支'] == '支出') &
        (df['交易分类'] == category)
    ]

    monthly_stats = category_df.groupby('月份').agg({
        '金额': ['sum', 'count', 'mean'],
        '交易时间': lambda x: len(x.dt.date.unique())
    }).round(2)

    monthly_stats.columns = ['total', 'transactions', 'avg_amount', 'active_days']

    monthly_stats['daily_avg'] = (monthly_stats['total'] / monthly_stats['active_days']).round(2)
    monthly_stats['mom_rate'] = (monthly_stats['total'].pct_change() * 100).round(2)

    total_expense = df[
        (df['收/支'] == '支出')
    ].groupby('月份')['金额'].sum()
    monthly_stats['percentage'] = (monthly_stats['total'] / total_expense * 100).round(2)

    return jsonify({
        'months': monthly_stats.index.tolist(),
        'total': monthly_stats['total'].tolist(),
        'transactions': monthly_stats['transactions'].tolist(),
        'avg_amount': monthly_stats['avg_amount'].tolist(),
        'daily_avg': monthly_stats['daily_avg'].tolist(),
        'mom_rate': monthly_stats['mom_rate'].fillna(0).tolist(),
        'percentage': monthly_stats['percentage'].tolist(),
        'summary': {
            'total_amount': category_df['金额'].sum().round(2),
            'total_transactions': len(category_df),
            'max_month': monthly_stats['total'].idxmax(),
            'max_amount': monthly_stats['total'].max().round(2),
            'min_month': monthly_stats['total'].idxmin(),
            'min_amount': monthly_stats['total'].min().round(2),
            'avg_monthly': monthly_stats['total'].mean().round(2)
        }
    })
