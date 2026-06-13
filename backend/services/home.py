"""
首页概览服务 —— 一次请求拿全首页仪表盘要的数据(性能:避免首页发 5 个请求)。

口径全部走「资金性质」真实口径,与对账中心/收入分析一致:
- 真实消费 = 资金性质「消费」;真实收入 = 工资收入+投资收益+其他收入。
"""
import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

INCOME_NATURES = ('工资收入', '投资收益', '其他收入')


def _r(v, n=2):
    try:
        return round(float(v), n)
    except Exception:
        return 0.0


def _expense_df(df):
    d = df
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    if '资金性质' in d.columns:
        return d[d['资金性质'] == '消费']
    return d[d['收/支'] == '支出']


def _income_total(df, mask):
    d = df[mask]
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    if '资金性质' in d.columns:
        return _r(d[d['资金性质'].isin(INCOME_NATURES)]['金额'].sum())
    return _r(d[d['收/支'] == '收入']['金额'].sum())


def overview(df, uid=None):
    now = datetime.now()
    y, m = now.year, now.month
    exp = _expense_df(df)

    # 本月 / 上月真实消费
    this_m = exp[(exp['交易时间'].dt.year == y) & (exp['交易时间'].dt.month == m)]
    lm_y, lm_m = (y, m - 1) if m > 1 else (y - 1, 12)
    last_m = exp[(exp['交易时间'].dt.year == lm_y) & (exp['交易时间'].dt.month == lm_m)]
    this_exp = _r(this_m['金额'].sum())
    last_exp = _r(last_m['金额'].sum())

    # 今年真实消费/收入/结余
    year_mask = df['交易时间'].dt.year == y
    year_exp = _r(exp[exp['交易时间'].dt.year == y]['金额'].sum())
    year_inc = _income_total(df, year_mask)

    # 近 6 个月消费趋势
    months = []
    for i in range(5, -1, -1):
        ym = (now.year, now.month)
        mm = now.month - i
        yy = now.year
        while mm <= 0:
            mm += 12
            yy -= 1
        sub = exp[(exp['交易时间'].dt.year == yy) & (exp['交易时间'].dt.month == mm)]
        months.append({'month': f"{yy}-{mm:02d}", 'amount': _r(sub['金额'].sum())})

    # 本月 top 分类
    top_cat = []
    if len(this_m):
        g = this_m.groupby('交易分类')['金额'].sum().sort_values(ascending=False).head(6)
        top_cat = [{'category': str(k), 'amount': _r(v)} for k, v in g.items()]

    # 近期大额消费(今年,>=1000,最近 5 笔)
    big = exp[(exp['交易时间'].dt.year == y) & (exp['金额'] >= 1000)].sort_values('交易时间', ascending=False).head(5)
    recent_large = [{
        'time': r['交易时间'].strftime('%m-%d'), 'amount': _r(r['金额']),
        'category': str(r.get('交易分类', '')), 'desc': str(r.get('商品说明', ''))[:20],
        'counterparty': str(r.get('交易对方', ''))[:16],
    } for _, r in big.iterrows()]

    # 净资产(最新快照)
    net = None
    if uid:
        try:
            from services import networth as nw
            t = nw.trend(uid)
            if t:
                net = {'net': t[-1]['net'], 'date': t[-1]['date'],
                       'assets': t[-1]['assets'], 'liabilities': t[-1]['liabilities']}
        except Exception:
            logger.exception("首页净资产读取失败")

    # 预算执行(本月)
    budget = None
    if uid:
        try:
            from services import budget as bud
            st = bud.status(uid, df, y, m)
            if st.get('has_budget'):
                budget = st
        except Exception:
            logger.exception("首页预算读取失败")

    total_count = int(len(df))
    date_range = None
    if total_count:
        date_range = [df['交易时间'].min().strftime('%Y-%m-%d'), df['交易时间'].max().strftime('%Y-%m-%d')]

    return {
        'today': now.strftime('%Y-%m-%d'),
        'current_month': f"{y}-{m:02d}",
        'this_month_expense': this_exp,
        'last_month_expense': last_exp,
        'mom_pct': _r((this_exp - last_exp) / last_exp * 100, 1) if last_exp else None,
        'year_expense': year_exp,
        'year_income': year_inc,
        'year_balance': _r(year_inc - year_exp),
        'monthly_trend': months,
        'top_categories': top_cat,
        'recent_large': recent_large,
        'net_worth': net,
        'budget': budget,
        'total_count': total_count,
        'date_range': date_range,
    }
