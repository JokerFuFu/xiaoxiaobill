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


@analysis_bp.route('/api/transactions')
def get_transactions():
    """获取交易记录列表（支持分页和筛选）"""
    try:
        df = load_alipay_data()

        # 渠道标签（与渠道分析页同口径：同卡号跨平台归并）。在全集上计算，保证下拉选项稳定。
        _metas, _ = _build_channel_metas(df)
        df = df.assign(_channel=[m['label'] for m in _metas])

        page = request.args.get('page', DEFAULT_PAGE, type=int)
        per_page = request.args.get('per_page', DEFAULT_PER_PAGE, type=int)
        per_page = min(per_page, MAX_PER_PAGE)

        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        date = request.args.get('date')
        hour = request.args.get('hour', type=int)
        category = request.args.get('category')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        type_ = request.args.get('type')
        search_query = request.args.get('search')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        source = request.args.get('source')
        channel = request.args.get('channel')
        member = request.args.get('member')
        counterparty = request.args.get('counterparty')   # 交易对方(子串)
        desc = request.args.get('desc')                   # 商品说明(子串)
        status = request.args.get('status')               # 交易状态(精确)
        nature = request.args.get('nature')               # 资金性质(精确)
        view = request.args.get('view', 'normal')  # normal=收支(排除转账) / transfer=转账记录

        # 渠道/状态/资金性质 下拉选项（全集去退款后，按笔数倒序，稳定不随其它筛选漂移）
        _opt_df = df[~df['是否退款'].fillna(False)] if '是否退款' in df.columns else df
        _opt_counts = _opt_df['_channel'].value_counts()
        channel_options = [{'label': str(k), 'count': int(v)} for k, v in _opt_counts.items()]
        if '交易状态' in _opt_df.columns:
            _st_counts = _opt_df['交易状态'].astype(str).replace('nan', '').value_counts()
            status_options = [{'label': str(k), 'count': int(v)} for k, v in _st_counts.items() if str(k).strip()]
        else:
            status_options = []
        if '资金性质' in _opt_df.columns:
            _nt_counts = _opt_df['资金性质'].astype(str).value_counts()
            nature_options = [{'label': str(k), 'count': int(v)} for k, v in _nt_counts.items() if str(k).strip()]
        else:
            nature_options = []

        # 应用筛选条件
        if type_:
            df = df[df['收/支'] == type_]
        if source:
            df = df[df['来源'] == source]
        if member and '成员' in df.columns:
            df = df[df['成员'] == member]
        if channel:
            df = df[df['_channel'] == channel]
        if counterparty:
            df = df[df['交易对方'].astype(str).str.contains(counterparty, case=False, na=False, regex=False)]
        if desc:
            df = df[df['商品说明'].astype(str).str.contains(desc, case=False, na=False, regex=False)]
        if status and '交易状态' in df.columns:
            df = df[df['交易状态'].astype(str) == status]
        if nature and '资金性质' in df.columns:
            df = df[df['资金性质'].astype(str) == nature]
        if start_date:
            df = df[df['交易时间'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['交易时间'] < pd.to_datetime(end_date) + pd.Timedelta(days=1)]

        if search_query:
            mask = (
                df['商品说明'].astype(str).str.contains(search_query, case=False, na=False) |
                df['交易对方'].astype(str).str.contains(search_query, case=False, na=False) |
                df['交易分类'].astype(str).str.contains(search_query, case=False, na=False)
            )
            df = df[mask]

        if year:
            df = df[df['交易时间'].dt.year == year]
        if month:
            df = df[df['交易时间'].dt.month == month]
        if date:
            df = df[df['日期'] == date]
        if hour is not None:
            df = df[df['交易时间'].dt.hour == hour]
        if category:
            df = df[df['交易分类'] == category]
        if min_amount:
            df = df[df['金额'] >= min_amount]
        if max_amount:
            df = df[df['金额'] <= max_amount]

        df = df[~df['是否退款']]
        # 转账判定：平台转账/红包 + 银行 转入/转出（自转/对外/理财/还款/搬运）+ 历史不计收支
        is_transfer = df['交易分类'].isin(['转账', '转账红包']) | df['收/支'].isin(['不计收支', '转入', '转出'])
        if view == 'transfer':
            df = df[is_transfer]          # 转账记录 = 交易记录的子集
        # 交易记录(normal) = 全部交易(含转账)，转账记录是其子集
        df = df.sort_values('交易时间', ascending=False)

        # 筛选结果统计汇总（对整个筛选集，不只当前页）
        income_sum = float(df[df['收/支'] == '收入']['金额'].sum())
        expense_sum = float(df[df['收/支'] == '支出']['金额'].sum())
        tin_sum = float(df[df['收/支'] == '转入']['金额'].sum())
        tout_sum = float(df[df['收/支'] == '转出']['金额'].sum())
        internal_sum = float(df[df['收/支'] == '不计收支']['金额'].sum())
        summary = {
            'count': int(len(df)),
            'income': round(income_sum, 2),
            'expense': round(expense_sum, 2),
            'net': round(income_sum - expense_sum, 2),
            'transfer_in': round(tin_sum, 2),
            'transfer_out': round(tout_sum, 2),
            'internal': round(internal_sum, 2),
        }

        # 图表数据（基于整个筛选集，供前端饼图/折线图）
        chart = {'by_category': [], 'by_month': []}
        if len(df) > 0:
            # 饼图：交易记录只看消费(支出)分类；转账记录看转账分类(含不计收支搬运)
            cat_df = df if view == 'transfer' else df[df['收/支'] == '支出']
            if len(cat_df) > 0:
                cat_g = cat_df.groupby('交易分类')['金额'].sum().abs().sort_values(ascending=False).head(10)
                chart['by_category'] = [{'name': str(k), 'value': round(float(v), 2)} for k, v in cat_g.items()]
            tmp = df.copy()
            tmp['_m'] = tmp['交易时间'].dt.strftime('%Y-%m')
            for m, g in tmp.groupby('_m'):
                chart['by_month'].append({
                    'month': m,
                    'income': round(float(g[g['收/支'] == '收入']['金额'].sum()), 2),
                    'expense': round(float(g[g['收/支'] == '支出']['金额'].sum()), 2),
                    'transfer_in': round(float(g[g['收/支'] == '转入']['金额'].sum()), 2),
                    'transfer_out': round(float(g[g['收/支'] == '转出']['金额'].sum()), 2),
                    'internal': round(float(g[g['收/支'] == '不计收支']['金额'].sum()), 2),
                })
            chart['by_month'].sort(key=lambda x: x['month'])

        total_records = len(df)
        total_pages = (total_records + per_page - 1) // per_page
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_records)

        page_df = df.iloc[start_idx:end_idx]

        transactions = []
        for _, row in page_df.iterrows():
            transactions.append({
                'time': row['交易时间'].strftime('%Y-%m-%d %H:%M:%S'),
                'description': str(row['商品说明']),
                'category': str(row['交易分类']),
                'type': str(row['收/支']),
                'amount': float(row['金额']),
                'status': str(row['交易状态']) if pd.notna(row.get('交易状态')) else '交易成功',
                'counterparty': str(row.get('交易对方', '')) if pd.notna(row.get('交易对方')) else '',
                'channel': str(row['_channel']) if pd.notna(row.get('_channel')) else '',
                'nature': str(row.get('资金性质', '')) if pd.notna(row.get('资金性质')) else ''
            })

        return jsonify({
            'success': True,
            'transactions': transactions,
            'summary': summary,
            'chart': chart,
            'channel_options': channel_options,
            'status_options': status_options,
            'nature_options': nature_options,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_records': total_records
            }
        })

    except Exception as e:
        logger.error(f"获取交易记录时出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'获取交易记录失败: {str(e)}'
        }), 500


@analysis_bp.route('/api/top_transactions')
def get_top_transactions():
    """获取大额交易记录"""
    try:
        limit = int(request.args.get('limit', 10))
        min_amount = float(request.args.get('min_amount', 1000))

        df = load_alipay_data()

        expense_df = df[df['收/支'] == '支出'].copy()
        large_transactions = expense_df[expense_df['金额'] >= min_amount]
        top_transactions = large_transactions.nlargest(limit, '金额')

        transactions = []
        for _, row in top_transactions.iterrows():
            transactions.append({
                'time': row['交易时间'].strftime('%Y-%m-%d %H:%M:%S'),
                'date': row['交易时间'].strftime('%Y-%m-%d'),
                'category': row['交易分类'],
                'description': row['商品说明'],
                'amount': float(row['金额']),
                'status': row['交易状态'],
                'counterparty': row.get('交易对方', '')
            })

        return jsonify({
            'success': True,
            'transactions': transactions
        })

    except Exception as e:
        logger.error(f"获取大额交易记录时出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'获取大额交易记录失败: {str(e)}'
        }), 500


# ============ 时间分析 API ============
