"""
订阅 / 定期扣费识别 —— 两路合并,兼顾"转账代付的订阅"与"规律账单"。

实测发现:很多订阅(尤其 GPT/Claude/Codex/Manus)是**转给个人**代充的,资金性质是「转账往来」
而非「消费」,只扫消费会整类漏掉;同时账单里大量 ¥0.6 的"会员"垃圾(影视/云手机),
用泛"会员"关键词会误伤。所以:

A. 关键词服务 pass:扫所有对外支出/转出(含转账),只认**具体服务名**(GPT/Claude/Manus/Kimi/
   剪映/WPS/腾讯视频/车位/自动续费…),按服务聚合 → 捞回转账代付订阅,且避开泛会员垃圾。
B. 规律账单 pass:在真实消费里按对手方找按月/季/年规律重复且金额稳定的(房租/税费/水电),
   排除已被 A 认领的、打码个人名、吃饭购物类目。
两路合并去重(A 认领过的流水索引,B 不再计)。
"""
import logging
import re
from statistics import median

import pandas as pd

logger = logging.getLogger(__name__)

# ===== A. 关键词服务(高精度,只认具体服务名) =====
# (服务标签, 正则, 归类)。顺序即优先级,AI 类最先。
_SERVICE_RULES = [
    ('AI 编程/对话(GPT/Claude/Codex)',
     re.compile(r'gpt|chatgpt|claude|codex|openai|cursor|copilot|grok|perplexity|midjourney|gemini\s*(pro|adv)', re.I), '订阅会员'),
    ('Manus', re.compile(r'manus', re.I), '订阅会员'),
    ('Kimi', re.compile(r'kimi|月之暗面', re.I), '订阅会员'),
    ('剪映', re.compile(r'剪映', re.I), '订阅会员'),
    ('WPS 会员', re.compile(r'wps\s*(大|超级)?会员|wps大会员', re.I), '订阅会员'),
    ('腾讯视频/会议', re.compile(r'腾讯视频|腾讯会议|腾讯文档', re.I), '订阅会员'),
    ('B站大会员', re.compile(r'哔哩哔哩大会员|b站大会员', re.I), '订阅会员'),
    ('音乐会员', re.compile(r'qq音乐.*会员|网易云音乐|spotify', re.I), '订阅会员'),
    ('视频会员', re.compile(r'爱奇艺|优酷会员|芒果\s*tv|netflix|disney', re.I), '订阅会员'),
    ('百度网盘', re.compile(r'百度网盘(超级)?会员|百度网盘.*svip', re.I), '订阅会员'),
    ('云盘/笔记/效率', re.compile(r'notion|adobe|office\s*365|microsoft\s*365|processon|cubox|飞书', re.I), '订阅会员'),
    ('车位租金', re.compile(r'车位', re.I), '房租物业'),
    ('其他自动续费', re.compile(r'自动续费|连续包月|连续包年|订阅服务|续订服务', re.I), '订阅会员'),
]


def _match_service(text):
    for label, pat, cat in _SERVICE_RULES:
        if pat.search(text):
            return label, cat
    return None, None


# ===== B. 规律账单的关键词/分类归类 =====
_TYPE_RULES = [
    ('税费', re.compile(r'税务局|个税|社保|社会保险|公积金|医保')),
    ('公共事业', re.compile(r'电力|供电|自来水|水务|燃气|天然气|话费|流量|宽带|物业|移动|联通|电信|广电|国网')),
    ('房租物业', re.compile(r'房租|租金|公寓|长租')),
    ('保险', re.compile(r'保险|保费|人寿|财险|健康险|重疾')),
]
_CAT_TYPE = [('房租物业', ('住房',)), ('公共事业', ('生活缴费', '缴费', '通讯', '通信')), ('保险', ('保险',))]
_CONSUMPTION_CATS = ('餐饮美食', '美食', '日用百货', '服饰装扮', '数码电器', '母婴亲子',
                     '美容美发', '商户消费', '超市便利', '运动户外', '生鲜果蔬', '酒店旅游', '交通出行')


def _classify_bill(text, cat=''):
    for name, pat in _TYPE_RULES:
        if pat.search(text):
            return name
    for name, cats in _CAT_TYPE:
        if any(c in cat for c in cats):
            return name
    return None


def _cadence(days_sorted):
    if len(days_sorted) < 2:
        return None, 0, 0
    gaps = [(days_sorted[i + 1] - days_sorted[i]).days for i in range(len(days_sorted) - 1)]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return None, 0, 0
    g = median(gaps)
    if 22 <= g <= 38:
        return '每月', 1.0, g
    if 12 <= g < 22:
        return '每两周', 2.0, g
    if 80 <= g <= 100:
        return '每季', 1 / 3, g
    if 175 <= g <= 200:
        return '每半年', 1 / 6, g
    if 330 <= g <= 400:
        return '每年', 1 / 12, g
    if g < 12:
        return '高频', 30.0 / g, g
    return '不定期', 30.0 / g if g else 0, g


def _span_months(dates):
    """首末跨度(月),至少 1。"""
    d = sorted(dates)
    return max(1, round((d[-1] - d[0]).days / 30) + 1)


def _keyword_pass(df):
    """A 路:关键词服务。返回 (items, claimed_index_set)。"""
    d = df.copy()
    d = d[d['收/支'].isin(['支出', '转出'])]
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    if d.empty:
        return [], set()
    text = (d['交易对方'].astype(str).fillna('') + ' ' + d['商品说明'].astype(str).fillna(''))
    groups = {}
    claimed = set()
    for idx in d.index:
        label, cat = _match_service(text[idx])
        if not label:
            continue
        claimed.add(idx)
        groups.setdefault(label, {'cat': cat, 'idx': []})['idx'].append(idx)

    items = []
    for label, info in groups.items():
        g = d.loc[info['idx']]
        if len(g) < 2:        # 单次一般是试用/一次性,不算订阅
            continue
        amts = g['金额'].astype(float)
        dates = list(g['交易时间'])
        span = _span_months(dates)
        total = float(amts.sum())
        parties = [p for p in g['交易对方'].astype(str).unique() if p and p != 'nan'][:4]
        via = '转账代付' if (g['收/支'] == '转出').mean() >= 0.5 else '直接扣费'
        last = g['交易时间'].max()
        items.append({
            'merchant': label, 'type': info['cat'], 'cadence': '按需/不定期',
            'amount': round(float(amts.median()), 2),
            'monthly_cost': round(total / span, 2), 'annual_cost': round(total / span * 12, 2),
            'count': int(len(g)), 'months': int(g['交易时间'].dt.strftime('%Y-%m').nunique()),
            'cv': None, 'last_date': last.strftime('%Y-%m-%d'), 'next_due': None,
            'total_paid': round(total, 2), 'via': via, 'parties': parties,
            'sample': str(g.sort_values('交易时间')['商品说明'].iloc[-1])[:48],
        })
    return items, claimed


def _real_consumption(df, claimed):
    from services.nature import NATURE_COL, EXPENSE_NATURE
    if NATURE_COL in df.columns:
        d = df[df[NATURE_COL] == EXPENSE_NATURE].copy()
    else:
        d = df[df['收/支'] == '支出'].copy()
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d[~d.index.isin(claimed)]


def _regular_pass(df, claimed):
    """B 路:真实消费里的规律账单(房租/税费/水电等)。"""
    con = _real_consumption(df, claimed)
    if con is None or len(con) == 0:
        return []
    con = con.copy()
    con['_party'] = con['交易对方'].astype(str).fillna('').str.strip()
    con = con[con['_party'].str.len() > 1]

    items = []
    for party, g in con.groupby('_party'):
        if len(g) < 3 or '*' in party:
            continue
        g = g.sort_values('交易时间')
        months = g['交易时间'].dt.strftime('%Y-%m').nunique()
        if months < 3:
            continue
        amts = g['金额'].astype(float)
        mean_amt = amts.mean()
        cv = (amts.std() / mean_amt) if mean_amt else 9
        cat = str(g['交易分类'].mode().iloc[0]) if '交易分类' in g.columns and len(g) else ''
        ttype = _classify_bill(party + ' ' + ' '.join(g['商品说明'].astype(str).head(5).tolist()), cat)
        label, per_month, gap = _cadence(list(g['交易时间']))
        regular = label in ('每月', '每两周', '每季', '每半年', '每年')
        stable = cv < 0.25
        if ttype:
            if not (regular or stable):
                continue
        else:
            if not (regular and stable):
                continue
            if any(c in cat for c in _CONSUMPTION_CATS):
                continue
            ttype = '其他定期'
        med = round(float(amts.median()), 2)
        monthly = round(med * per_month, 2) if per_month else med
        last = g['交易时间'].max()
        items.append({
            'merchant': party[:40], 'type': ttype, 'cadence': label,
            'amount': med, 'monthly_cost': monthly, 'annual_cost': round(monthly * 12, 2),
            'count': int(len(g)), 'months': int(months), 'cv': round(float(cv), 2),
            'last_date': last.strftime('%Y-%m-%d'),
            'next_due': (last + pd.Timedelta(days=int(gap))).strftime('%Y-%m-%d') if gap else None,
            'total_paid': round(float(amts.sum()), 2), 'via': '直接扣费', 'parties': [],
            'sample': str(g['商品说明'].iloc[-1])[:48],
        })
    return items


def detect(df, year=None):
    out = {'count': 0, 'monthly_total': 0.0, 'annual_total': 0.0, 'items': [], 'by_type': []}
    if df is None or len(df) == 0:
        return out
    kw_items, claimed = _keyword_pass(df)
    reg_items = _regular_pass(df, claimed)
    items = kw_items + reg_items
    items.sort(key=lambda x: -x['monthly_cost'])

    by_type = {}
    for it in items:
        b = by_type.setdefault(it['type'], {'type': it['type'], 'count': 0, 'monthly_cost': 0.0})
        b['count'] += 1
        b['monthly_cost'] = round(b['monthly_cost'] + it['monthly_cost'], 2)
    return {
        'count': len(items),
        'monthly_total': round(sum(i['monthly_cost'] for i in items), 2),
        'annual_total': round(sum(i['annual_cost'] for i in items), 2),
        'items': items,
        'by_type': sorted(by_type.values(), key=lambda x: -x['monthly_cost']),
    }
