"""
收入分析服务 —— 收支表的「收入侧」深挖。

三个板块(均基于资金性质口径,与对账中心同源):
1. salary   薪资分析:月度发薪序列(全历史)、平均/中位月薪、发薪日、奖金月识别、
            同比、储蓄率(工资 vs 真实消费)、口径审计(工资卡锚点)
2. invest   理财收益:已实现利息/结息/分红(注:基金市值涨跌不在流水里,只能看已实现部分)
3. other    其他收入:按来源分组(闲鱼/医保理赔/经营收款…)

薪资口径锚点:用户的工资只进指定的工资卡(可配,默认从工资行众数渠道推断)。
锚点既用于识别,也用于反向审计:「标了工资但不在工资卡」「工资卡大额入账却没标工资」。
"""
import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

SALARY_MIN = 1000          # 低于此金额的"工资收入"行不视为发薪(防零星误标)
BONUS_RATIO = 1.6          # 月发薪额 > 中位数×此倍数 → 标记奖金月
MISS_SALARY_MIN = 5000     # 工资卡大额入账未标工资的审计阈值


def _clean(df, year=None):
    d = df
    if year:
        d = d[d['交易时间'].dt.year == int(year)]
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d


def _r(v, n=2):
    try:
        return round(float(v), n)
    except Exception:
        return 0.0


def _channel_series(df):
    """每行的渠道标签(复用渠道分析口径);失败回落到 收/付款方式。"""
    try:
        from services.analysis import _build_channel_metas
        metas, _ = _build_channel_metas(df)
        return pd.Series([m.get('label', '') for m in metas], index=df.index)
    except Exception:
        logger.exception("渠道标签构建失败,回落付款方式")
        if '收/付款方式' in df.columns:
            return df['收/付款方式'].astype(str).fillna('')
        return pd.Series([''] * len(df), index=df.index)


# ============ 薪资分析 ============
def salary_analysis(df, salary_channel_hint=None):
    """薪资分析(全历史,薪资趋势跨年才有意义)。"""
    d = df
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    if '资金性质' not in d.columns:
        return {'months': [], 'audit': {}, 'stats': {}}

    chan = _channel_series(df).reindex(d.index)
    sal = d[(d['资金性质'] == '工资收入') & (d['金额'] >= SALARY_MIN)]
    if sal.empty:
        return {'months': [], 'audit': {'salary_channel': None, 'off_channel': [], 'missed': []}, 'stats': {}}

    # 工资卡锚点:外部指定 > 工资行的众数渠道
    sal_chan = chan.reindex(sal.index)
    salary_channel = salary_channel_hint or (sal_chan.mode().iloc[0] if len(sal_chan.mode()) else '')

    # 月度发薪序列(同月多笔合并,记录发薪日与笔数)
    months = []
    g = sal.groupby(sal['交易时间'].dt.strftime('%Y-%m'))
    for mo, rows in g:
        months.append({
            'month': mo,
            'amount': _r(rows['金额'].sum()),
            'count': int(len(rows)),
            'payday': int(rows['交易时间'].dt.day.min()),
            'desc': ' / '.join(sorted(set(str(x)[:8] for x in rows.get('商品说明', pd.Series(dtype=str)).fillna('')))[:2]),
        })
    months.sort(key=lambda x: x['month'])

    amounts = [m['amount'] for m in months]
    med = _r(pd.Series(amounts).median())
    for m in months:
        m['is_bonus'] = bool(med and m['amount'] > med * BONUS_RATIO)

    # 连续性:首末月之间漏发的月份
    all_range = pd.period_range(months[0]['month'], months[-1]['month'], freq='M').strftime('%Y-%m')
    have = {m['month'] for m in months}
    missing_months = [m for m in all_range if m not in have]

    # 储蓄率:逐月 工资 vs 真实消费(消费口径)
    cons = d[d['资金性质'] == '消费']
    cons_m = cons.groupby(cons['交易时间'].dt.strftime('%Y-%m'))['金额'].sum() if len(cons) else pd.Series(dtype=float)
    for m in months:
        c = _r(cons_m.get(m['month'], 0.0))
        m['consume'] = c
        m['saving_rate'] = _r((m['amount'] - c) / m['amount'] * 100, 1) if m['amount'] else None

    # 年度合计与同比
    yearly = {}
    for m in months:
        y = m['month'][:4]
        yearly.setdefault(y, {'amount': 0.0, 'months': 0})
        yearly[y]['amount'] = _r(yearly[y]['amount'] + m['amount'])
        yearly[y]['months'] += 1
    years_sorted = sorted(yearly)
    yoy = None
    if len(years_sorted) >= 2:
        cur_y, prev_y = years_sorted[-1], years_sorted[-2]
        # 用月均比,避免不满整年失真
        cur_avg = yearly[cur_y]['amount'] / max(1, yearly[cur_y]['months'])
        prev_avg = yearly[prev_y]['amount'] / max(1, yearly[prev_y]['months'])
        if prev_avg:
            yoy = _r((cur_avg - prev_avg) / prev_avg * 100, 1)

    recent12 = months[-12:]
    paydays = [m['payday'] for m in months if not m['is_bonus']] or [m['payday'] for m in months]
    stats = {
        'salary_channel': salary_channel,
        'total': _r(sum(amounts)),
        'months_count': len(months),
        'avg_recent12': _r(sum(m['amount'] for m in recent12) / max(1, len(recent12))),
        'median': med,
        'max_month': max(months, key=lambda m: m['amount'])['month'],
        'max_amount': _r(max(amounts)),
        'typical_payday': int(pd.Series(paydays).mode().iloc[0]) if paydays else None,
        'yoy_avg_pct': yoy,
        'yearly': [{'year': y, **yearly[y]} for y in years_sorted],
        'avg_saving_rate': _r(pd.Series([m['saving_rate'] for m in recent12 if m['saving_rate'] is not None]).mean(), 1)
                           if any(m['saving_rate'] is not None for m in recent12) else None,
        'missing_months': missing_months,
    }

    # 口径审计(工资卡锚点)
    off = sal[sal_chan != salary_channel] if salary_channel else sal.iloc[0:0]
    off_rows = [{'time': r['交易时间'].strftime('%Y-%m-%d'), 'amount': _r(r['金额']),
                 'channel': str(sal_chan.get(i, '')), 'desc': str(r.get('商品说明', ''))[:20]}
                for i, r in off.head(10).iterrows()]
    # 工资卡上的大额入账却未标工资(疑似漏标:奖金/报销走了别的摘要)。
    # 只看「其他收入/报销」桶——漏标的工资必然兜底落在这里;
    # 转账往来/投资申赎/内部流转是资金周转,不是工资,列出来只会刷屏。
    inflow = d[(d['收/支'].isin(['收入', '转入'])) & (d['金额'] >= MISS_SALARY_MIN) &
               d['资金性质'].isin(['其他收入', '报销'])]
    inflow_chan = chan.reindex(inflow.index)
    missed = inflow[inflow_chan == salary_channel] if salary_channel else inflow.iloc[0:0]
    missed_rows = [{'time': r['交易时间'].strftime('%Y-%m-%d'), 'amount': _r(r['金额']),
                    'nature': str(r.get('资金性质', '')), 'desc': str(r.get('商品说明', ''))[:20],
                    'counterparty': str(r.get('交易对方', ''))[:16]}
                   for _, r in missed.sort_values('金额', ascending=False).head(10).iterrows()]

    return {'months': months, 'stats': stats,
            'audit': {'salary_channel': salary_channel, 'off_channel': off_rows, 'missed': missed_rows}}


# ============ 理财收益 ============
def invest_income(df, year=None):
    d = _clean(df, year)
    if '资金性质' not in d.columns:
        return {'months': [], 'total': 0, 'by_channel': []}
    inv = d[d['资金性质'] == '投资收益']
    chan = _channel_series(df).reindex(inv.index)
    months = [{'month': mo, 'amount': _r(v)} for mo, v in
              inv.groupby(inv['交易时间'].dt.strftime('%Y-%m'))['金额'].sum().items()]
    months.sort(key=lambda x: x['month'])
    cum = 0.0
    for m in months:
        cum = _r(cum + m['amount'])
        m['cum'] = cum
    by_chan = [{'channel': str(k), 'amount': _r(v), 'count': int(c)}
               for (k, v, c) in ((k, g['金额'].sum(), len(g)) for k, g in inv.groupby(chan))]
    by_chan.sort(key=lambda x: -x['amount'])
    # 上下文:在外投资本金净额(申购-赎回,绝对额近似)
    sub = d[d['资金性质'] == '投资申赎']
    out_ = _r(sub[sub['收/支'].isin(['支出', '转出'])]['金额'].sum())
    in_ = _r(sub[sub['收/支'].isin(['收入', '转入'])]['金额'].sum())
    return {'months': months, 'total': _r(inv['金额'].sum()), 'count': int(len(inv)),
            'by_channel': by_chan,
            'principal': {'subscribe': out_, 'redeem': in_, 'net_out': _r(out_ - in_)},
            'note': '仅含已实现的利息/结息/分红;基金理财的市值涨跌不在流水里,需在「资产负债」记快照体现。'}


# ============ 其他收入 ============
_OTHER_GROUPS = [
    ('闲鱼/二手', re.compile(r'闲鱼|转卖|二手')),
    ('医保/理赔', re.compile(r'医保|理赔|保险金|赔付|赔偿')),
    ('经营收款', re.compile(r'经营|收款')),
    ('公积金', re.compile(r'公积')),
    # 平台个人买家收款(对方为 ****N 掩码,说明是商品名)——多为闲鱼等二手成交
    ('个人买家收款(疑似二手)', re.compile(r'\*{3,}')),
]


def other_income(df, year=None):
    d = _clean(df, year)
    if '资金性质' not in d.columns:
        return {'groups': [], 'months': [], 'total': 0}
    oth = d[d['资金性质'] == '其他收入']
    if oth.empty:
        return {'groups': [], 'months': [], 'total': 0, 'count': 0}
    text = (oth['交易分类'].astype(str).fillna('') + '|' +
            oth.get('交易对方', pd.Series([''] * len(oth), index=oth.index)).astype(str).fillna('') + '|' +
            oth.get('商品说明', pd.Series([''] * len(oth), index=oth.index)).astype(str).fillna(''))
    grp = pd.Series(['其他'] * len(oth), index=oth.index)
    for name, pat in reversed(_OTHER_GROUPS):   # 反向迭代保证列表前面的优先级更高
        grp[text.str.contains(pat, na=False)] = name
    groups = [{'group': str(k), 'amount': _r(g['金额'].sum()), 'count': int(len(g)),
               'top': [{'desc': str(r.get('商品说明', ''))[:24], 'amount': _r(r['金额']),
                        'time': r['交易时间'].strftime('%Y-%m-%d')}
                       for _, r in g.sort_values('金额', ascending=False).head(3).iterrows()]}
              for k, g in oth.groupby(grp)]
    groups.sort(key=lambda x: -x['amount'])
    months = [{'month': mo, 'amount': _r(v)} for mo, v in
              oth.groupby(oth['交易时间'].dt.strftime('%Y-%m'))['金额'].sum().items()]
    months.sort(key=lambda x: x['month'])
    return {'groups': groups, 'months': months, 'total': _r(oth['金额'].sum()), 'count': int(len(oth))}


# ============ 总览 ============
def overview(df, year=None):
    d = _clean(df, year)
    if '资金性质' not in d.columns:
        return {}
    out = {}
    for nat in ('工资收入', '投资收益', '其他收入', '报销', '退款'):
        sub = d[(d['资金性质'] == nat) & d['收/支'].isin(['收入', '转入'])]
        out[nat] = {'amount': _r(sub['金额'].sum()), 'count': int(len(sub))}
    real = _r(out['工资收入']['amount'] + out['投资收益']['amount'] + out['其他收入']['amount'])
    cons = _r(d[d['资金性质'] == '消费']['金额'].sum())
    return {'buckets': out, 'real_income': real, 'real_expense': cons,
            'saving': _r(real - cons),
            'saving_rate': _r((real - cons) / real * 100, 1) if real else None}


def full_report(df, year=None):
    return {
        'overview': overview(df, year),
        'salary': salary_analysis(df),     # 全历史(趋势跨年才有意义)
        'invest': invest_income(df, year),
        'other': other_income(df, year),
    }
