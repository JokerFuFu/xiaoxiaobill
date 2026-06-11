"""
对账中心服务 —— 让"没有双算"从「相信」变成「看见」。

四个审计视角:
1. waterfall   口径瀑布:总流出/总流入 如何一层层剥离到 真实消费/真实收入
2. feeds       平台喂养对账:银行/信用卡里"喂给支付宝/财付通"的钱 vs 平台侧刷卡消费
3. credit      信用卡对账:信用卡消费 vs 储蓄卡还款(滞后一个账期)
4. suspects    疑似双算:不同来源、同日同金额、都被计为「消费」的可疑对
"""
import logging
import re

import pandas as pd

from services.nature import NATURE_COL, INCOME_NATURES

logger = logging.getLogger(__name__)

# 平台侧"由银行卡出资"的付款方式特征
_CARD_PAY_RE = re.compile(r'银行|信用卡|储蓄卡|借记')
# 银行侧"喂给平台"的文本特征
_FEED_ALIPAY = re.compile(r'支付宝|alipay', re.I)
_FEED_WECHAT = re.compile(r'财付通|微信支付|微信红包|wxpay', re.I)

_OUT_DIRS = ('支出', '转出')
_IN_DIRS = ('收入', '转入')


def _clean(df, year=None):
    d = df
    if year:
        d = d[d['交易时间'].dt.year == int(year)]
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d


def _bucket(d, dirs):
    """按资金性质聚合某方向的行。"""
    sub = d[d['收/支'].isin(dirs)] if '收/支' in d.columns else d.iloc[0:0]
    if NATURE_COL not in sub.columns:
        return {'total': round(float(sub['金额'].sum()), 2) if len(sub) else 0.0,
                'count': int(len(sub)), 'buckets': []}
    g = sub.groupby(NATURE_COL)['金额'].agg(['sum', 'count'])
    buckets = [{'nature': str(k), 'amount': round(float(r['sum']), 2), 'count': int(r['count'])}
               for k, r in g.iterrows()]
    buckets.sort(key=lambda b: -b['amount'])
    return {'total': round(float(sub['金额'].sum()), 2), 'count': int(len(sub)), 'buckets': buckets}


def waterfall(df, year=None):
    """口径瀑布:流出侧从总流出剥到真实消费;流入侧剥到真实收入。"""
    d = _clean(df, year)
    out = _bucket(d, _OUT_DIRS)
    inn = _bucket(d, _IN_DIRS)
    neutral = d[d['收/支'] == '不计收支']
    real_expense = next((b['amount'] for b in out['buckets'] if b['nature'] == '消费'), 0.0)
    real_income = round(sum(b['amount'] for b in inn['buckets'] if b['nature'] in INCOME_NATURES), 2)
    return {
        'outflow': out, 'inflow': inn,
        'neutral': {'total': round(float(neutral['金额'].sum()), 2), 'count': int(len(neutral))},
        'real_expense': real_expense, 'real_income': real_income,
    }


def nature_breakdown(df, year=None):
    """资金性质 × 方向 交叉表(审计明细)。"""
    d = _clean(df, year)
    if d.empty:
        return []
    g = d.groupby([NATURE_COL, '收/支'])['金额'].agg(['sum', 'count'])
    rows = {}
    for (nat, zhi), r in g.iterrows():
        item = rows.setdefault(str(nat), {'nature': str(nat), 'total': 0.0, 'count': 0, 'dirs': {}})
        item['dirs'][str(zhi)] = {'amount': round(float(r['sum']), 2), 'count': int(r['count'])}
        item['total'] = round(item['total'] + float(r['sum']), 2)
        item['count'] += int(r['count'])
    out = list(rows.values())
    out.sort(key=lambda x: -x['total'])
    return out


def feeds(df, year=None):
    """平台喂养对账:逐月对比
       P = 平台侧由银行卡出资的流出(支出/转出/不计收支 且 付款方式含银行卡特征)
       B = 银行侧喂给该平台的流水(分类含 银行↔平台/平台代扣 或 文本含 支付宝/财付通)
       两边量级应大体相当;P >> B 提示银行流水缺月份,B >> P 提示银行侧多标。"""
    d = _clean(df, year)
    if d.empty or '来源' not in d.columns:
        return {'platforms': [], 'note': ''}
    pay = d['收/付款方式'].astype(str).fillna('') if '收/付款方式' in d.columns else pd.Series([''] * len(d), index=d.index)
    text = (d['交易分类'].astype(str).fillna('') + '|' +
            d.get('交易对方', pd.Series([''] * len(d), index=d.index)).astype(str).fillna('') + '|' +
            d.get('商品说明', pd.Series([''] * len(d), index=d.index)).astype(str).fillna(''))
    month = d['交易时间'].dt.strftime('%Y-%m')

    is_bank = d['来源'] == '银行'
    # 喂养=钱从银行流向平台。银行侧的"平台→银行回流"(提现/零钱通转出/退款回卡)必须剔除:
    # 有方向的行按 收/支 剔除入账;方向被折叠成不计收支的行按回流文本特征剔除。
    not_inflow = ~d['收/支'].isin(['收入', '转入'])
    not_backflow = ~text.str.contains(r'提现|零钱通转出|转出-到|资金回流|退款|退回', na=False)
    bank_feed_generic = is_bank & not_inflow & not_backflow & (
        text.str.contains('银行↔平台', na=False, regex=False) |
        text.str.contains('平台代扣', na=False, regex=False))

    platforms = []
    for pname, feed_re in (('支付宝', _FEED_ALIPAY), ('微信', _FEED_WECHAT)):
        # P:平台侧卡出资流出
        pm = (d['来源'] == pname) & d['收/支'].isin(['支出', '转出', '不计收支']) & pay.str.contains(_CARD_PAY_RE, na=False)
        p_monthly = d[pm].groupby(month[pm])['金额'].sum()
        # B:银行侧喂养(指名道姓的;银行↔平台类无平台名的单独归"未指明")
        bm = is_bank & not_inflow & not_backflow & text.str.contains(feed_re, na=False)
        b_monthly = d[bm].groupby(month[bm])['金额'].sum()
        months = sorted(set(p_monthly.index) | set(b_monthly.index))
        rows = []
        for mo in months:
            pv = round(float(p_monthly.get(mo, 0.0)), 2)
            bv = round(float(b_monthly.get(mo, 0.0)), 2)
            cov = round(bv / pv * 100, 1) if pv > 0 else None
            rows.append({'month': mo, 'platform_card_out': pv, 'bank_feed': bv, 'coverage': cov})
        platforms.append({
            'platform': pname,
            'platform_card_out_total': round(float(p_monthly.sum()), 2),
            'bank_feed_total': round(float(b_monthly.sum()), 2),
            'months': rows,
        })
    unnamed = bank_feed_generic & ~text.str.contains(_FEED_ALIPAY, na=False) & ~text.str.contains(_FEED_WECHAT, na=False)
    return {
        'platforms': platforms,
        'bank_feed_unnamed_total': round(float(d[unnamed]['金额'].sum()), 2),
        'note': '审计参考:两侧统计口径天然有差(退款回流、账期、未导入的月份),量级接近即健康;'
                '覆盖率长期过低通常意味着该平台消费走的卡的银行流水没有导入。',
    }


def credit(df, year=None):
    """信用卡对账:逐月 信用卡消费 vs 还款流出(同月 + 次月,信用卡有账期)。"""
    d = _clean(df, year)
    if d.empty:
        return {'months': [], 'consume_total': 0, 'repay_total': 0}
    try:
        from services.analysis import _build_channel_metas
        metas, _ = _build_channel_metas(df)
        kind = pd.Series([m.get('kind', '') for m in metas], index=df.index).reindex(d.index)
    except Exception:
        logger.exception("信用卡渠道识别失败,回落到付款方式关键词")
        pay = d['收/付款方式'].astype(str).fillna('') if '收/付款方式' in d.columns else pd.Series([''] * len(d), index=d.index)
        kind = pd.Series(['信用卡' if '信用卡' in p else '' for p in pay], index=d.index)

    month = d['交易时间'].dt.strftime('%Y-%m')
    consume_m = (kind == '信用卡') & (d['收/支'] == '支出')
    repay_m = (d[NATURE_COL] == '信用卡还款') & d['收/支'].isin(['支出', '转出', '不计收支']) & (kind != '信用卡')
    cm = d[consume_m].groupby(month[consume_m])['金额'].sum()
    rm = d[repay_m].groupby(month[repay_m])['金额'].sum()
    months = sorted(set(cm.index) | set(rm.index))
    rows = []
    for mo in months:
        nxt = (pd.Period(mo, freq='M') + 1).strftime('%Y-%m')   # 日历次月,不依赖数据连续性
        rows.append({
            'month': mo,
            'consume': round(float(cm.get(mo, 0.0)), 2),
            'repay_same': round(float(rm.get(mo, 0.0)), 2),
            'repay_next': round(float(rm.get(nxt, 0.0)), 2),
        })
    return {'months': rows,
            'consume_total': round(float(cm.sum()), 2),
            'repay_total': round(float(rm.sum()), 2),
            'note': '信用卡有账期,本月消费多在次月还款;总额量级接近即健康。还款仅统计非信用卡侧流出,避免两侧重复。'}


def suspects(df, year=None, min_amount=100, limit=60):
    """疑似双算:不同「来源」、同一天、同金额、都计为「消费」的行对。
       这是对"关键词识别喂养"这一弱环节的兜底审计。"""
    d = _clean(df, year)
    d = d[(d[NATURE_COL] == '消费') & (d['金额'] >= float(min_amount))]
    if d.empty or '来源' not in d.columns:
        return []
    d = d.copy()
    d['_day'] = d['交易时间'].dt.strftime('%Y-%m-%d')
    d['_amt'] = d['金额'].round(2)
    # 双算只可能发生在同一成员的不同来源之间(去重键同口径)
    keys = ['_day', '_amt'] + (['成员'] if '成员' in d.columns else [])
    groups = []
    for key, g in d.groupby(keys):
        day, amt = key[0], key[1]
        if g['来源'].nunique() < 2:
            continue
        rows = [{'time': r['交易时间'].strftime('%Y-%m-%d %H:%M'),
                 'source': str(r.get('来源', '')), 'counterparty': str(r.get('交易对方', ''))[:24],
                 'desc': str(r.get('商品说明', ''))[:30], 'pay': str(r.get('收/付款方式', ''))[:24],
                 'category': str(r.get('交易分类', ''))}
                for _, r in g.head(4).iterrows()]
        groups.append({'date': day, 'amount': float(amt), 'count': int(len(g)), 'rows': rows})
    groups.sort(key=lambda x: -x['amount'])
    return groups[:limit]


def full_report(df, year=None):
    return {
        'waterfall': waterfall(df, year),
        'nature_breakdown': nature_breakdown(df, year),
        'feeds': feeds(df, year),
        'credit': credit(df, year),
        'suspects': suspects(df, year),
    }
