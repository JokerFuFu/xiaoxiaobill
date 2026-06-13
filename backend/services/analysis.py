"""
数据分析服务

包含所有消费数据分析函数
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime

from config import CATEGORY_COLORS

logger = logging.getLogger(__name__)


# ============ 基础分析函数 ============

def analyze_merchants(df):
    """商家消费分析"""
    expense_df = df[df['收/支'] == '支出'].copy()

    # 按商家分组统计
    merchant_stats = expense_df.groupby('交易对方').agg({
        '金额': ['count', 'sum', 'mean'],
        '交易时间': lambda x: (x.max() - x.min()).days + 1
    }).round(2)

    merchant_stats.columns = ['交易次数', '总金额', '平均金额', '交易跨度']

    # 识别常客商家
    min_count = 2 if len(df) >= 50 else 1

    frequent_merchants = []
    for merchant, group in expense_df.groupby('交易对方'):
        if len(group) >= min_count:
            frequent_merchants.append({
                'name': merchant,
                'amount': float(group['金额'].sum()),
                'count': len(group),
                'last_visit': group['交易时间'].max().strftime('%Y-%m-%d')
            })

    # 按消费金额排序
    frequent_merchants.sort(key=lambda x: x['amount'], reverse=True)

    return {
        'merchant_stats': merchant_stats.to_dict('index'),
        'frequent_merchants': frequent_merchants[:20]
    }


def analyze_scenarios(df):
    """消费场景分析"""
    expense_df = df[df['收/支'] == '支出'].copy()

    # 1. 线上/线下消费
    online_keywords = [
        '淘宝', '天猫', '京东', '拼多多', '美团', '饿了么', 'App Store', 'Steam',
        'Apple Music', 'iCloud', '网易', '支付宝', '微信', '闲鱼', '得物'
    ]
    expense_df.loc[:, '消费场景'] = expense_df['交易对方'].apply(
        lambda x: '线上' if any(k in str(x) for k in online_keywords) else '线下'
    )

    # 2. 消费时段分析
    expense_df.loc[:, '消费时段'] = expense_df['交易时间'].dt.hour.map(
        lambda x: '清晨(6-9点)' if 6 <= x < 9
        else '上午(9-12点)' if 9 <= x < 12
        else '中午(12-14点)' if 12 <= x < 14
        else '下午(14-17点)' if 14 <= x < 17
        else '傍晚(17-20点)' if 17 <= x < 20
        else '晚上(20-23点)' if 20 <= x < 23
        else '深夜(23-6点)'
    )

    # 3. 消费金额层级
    expense_df.loc[:, '消费层级'] = expense_df['金额'].map(
        lambda x: '大额(1000+)' if x >= 1000
        else '中额(300-1000)' if x >= 300
        else '小额(100-300)' if x >= 100
        else '零花(0-100)'
    )

    scenario_stats = []

    # 线上/线下统计
    for scene, amount in expense_df.groupby('消费场景')['金额'].sum().items():
        scenario_stats.append({'name': scene, 'value': float(amount), 'category': '渠道'})

    # 时段统计
    for period, amount in expense_df.groupby('消费时段')['金额'].sum().items():
        scenario_stats.append({'name': period, 'value': float(amount), 'category': '时段'})

    # 金额层级统计
    for level, amount in expense_df.groupby('消费层级')['金额'].sum().items():
        scenario_stats.append({'name': level, 'value': float(amount), 'category': '层级'})

    return scenario_stats


def analyze_habits(df):
    """消费习惯分析"""
    expense_df = df[df['收/支'] == '支出'].copy()

    daily_expenses = expense_df.groupby(expense_df['交易时间'].dt.date)['金额'].sum()
    daily_avg = float(daily_expenses.mean())
    active_days = int(len(daily_expenses))

    weekend_expenses = expense_df[expense_df['交易时间'].dt.dayofweek.isin([5, 6])]['金额'].sum()
    weekend_ratio = float((weekend_expenses / expense_df['金额'].sum() * 100))

    # 固定支出比例
    monthly_merchant_counts = expense_df.groupby(['交易对方', expense_df['交易时间'].dt.to_period('M')]).size()
    merchant_months = monthly_merchant_counts.reset_index().groupby('交易对方').size()
    total_months = len(expense_df['交易时间'].dt.to_period('M').unique())

    recurring_merchants = merchant_months[merchant_months >= max(2, total_months * 0.8)].index
    fixed_expenses = expense_df[expense_df['交易对方'].isin(recurring_merchants)]['金额'].sum()
    fixed_ratio = float((fixed_expenses / expense_df['金额'].sum() * 100)) if expense_df['金额'].sum() > 0 else 0

    month_start = expense_df[expense_df['交易时间'].dt.day <= 5]['金额'].sum()
    month_start_ratio = float((month_start / expense_df['金额'].sum() * 100)) if expense_df['金额'].sum() > 0 else 0

    return {
        'daily_avg': round(daily_avg, 2),
        'active_days': active_days,
        'weekend_ratio': round(weekend_ratio, 1),
        'fixed_expenses': round(fixed_ratio, 1),
        'month_start_ratio': round(month_start_ratio, 1)
    }


def analyze_latte_factor(df):
    """拿铁因子分析：小额高频支出"""
    expense_df = df[df['收/支'] == '支出'].copy()

    small_expenses = expense_df[expense_df['金额'] < 30]
    merchant_counts = small_expenses.groupby('交易对方').size()

    frequent_merchants = merchant_counts[merchant_counts > 5].index
    latte_df = small_expenses[small_expenses['交易对方'].isin(frequent_merchants)]

    total_amount = latte_df['金额'].sum()
    item_count = len(latte_df)

    top_merchant = merchant_counts.idxmax() if not merchant_counts.empty else "未知"

    return {
        'total_amount': float(total_amount),
        'item_count': int(item_count),
        'top_merchant': top_merchant,
        'avg_price': float(total_amount / item_count) if item_count > 0 else 0
    }


def analyze_nighttime_spending(df):
    """深夜消费分析：22:00 - 04:00"""
    expense_df = df[df['收/支'] == '支出'].copy()

    night_mask = (expense_df['交易时间'].dt.hour >= 22) | (expense_df['交易时间'].dt.hour <= 4)
    night_df = expense_df[night_mask]

    total_night_spend = night_df['金额'].sum()
    total_spend = expense_df['金额'].sum()

    top_merchant = "无"
    if not night_df.empty:
        top_merchant = night_df.groupby('交易对方')['金额'].sum().idxmax()

    return {
        'total_amount': float(total_night_spend),
        'ratio': float((total_night_spend / total_spend * 100)) if total_spend > 0 else 0,
        'top_merchant': top_merchant,
        'transaction_count': len(night_df)
    }


def analyze_subscriptions(df):
    """隐形订阅分析：每月固定扣款"""
    expense_df = df[df['收/支'] == '支出'].copy()

    monthly_spend = expense_df.groupby(['交易对方', expense_df['交易时间'].dt.to_period('M')])['金额'].sum().reset_index()
    merchant_stats = monthly_spend.groupby('交易对方')['金额'].agg(['mean', 'std', 'count'])

    subs_merchants = merchant_stats[
        (merchant_stats['count'] >= 3) &
        (merchant_stats['std'] < 5)
    ]

    subscriptions = []
    for merchant in subs_merchants.index:
        avg_amount = merchant_stats.loc[merchant, 'mean']
        subscriptions.append({
            'name': merchant,
            'monthly_amount': float(avg_amount),
            'annual_amount': float(avg_amount * 12)
        })

    subscriptions.sort(key=lambda x: x['annual_amount'], reverse=True)

    return subscriptions


def analyze_inflation(df):
    """个人通胀率：客单价变化"""
    expense_df = df[df['收/支'] == '支出'].copy()

    expense_df['quarter'] = expense_df['交易时间'].dt.to_period('Q')
    quarterly_avg = expense_df.groupby('quarter')['金额'].mean()

    if len(quarterly_avg) < 2:
        return {'trend': 'stable', 'rate': 0}

    first_q = quarterly_avg.iloc[0]
    last_q = quarterly_avg.iloc[-1]

    rate = ((last_q - first_q) / first_q * 100) if first_q > 0 else 0

    return {
        'trend': 'up' if rate > 5 else ('down' if rate < -5 else 'stable'),
        'rate': float(rate),
        'first_avg': float(first_q),
        'last_avg': float(last_q)
    }


def analyze_brand_loyalty(df):
    """品牌忠诚度分析"""
    expense_df = df[df['收/支'] == '支出'].copy()

    if expense_df.empty:
        return None

    top_amount_merchant = expense_df.groupby('交易对方')['金额'].sum().idxmax()
    top_amount = expense_df.groupby('交易对方')['金额'].sum().max()

    top_count_merchant = expense_df.groupby('交易对方').size().idxmax()
    top_count = expense_df.groupby('交易对方').size().max()

    return {
        'top_amount': {
            'name': top_amount_merchant,
            'value': float(top_amount)
        },
        'top_count': {
            'name': top_count_merchant,
            'value': int(top_count)
        }
    }


def analyze_sankey(df):
    """桑基图数据：分类流向"""
    expense_df = df[df['收/支'] == '支出'].copy()

    # 按分类和来源统计
    category_source = expense_df.groupby(['交易分类', '来源'])['金额'].sum().reset_index()

    nodes = []
    links = []
    node_map = {}

    # 添加来源节点
    sources = expense_df['来源'].unique()
    for i, source in enumerate(sources):
        nodes.append({'name': source, 'category': 'source'})
        node_map[source] = i

    # 添加分类节点
    categories = expense_df['交易分类'].unique()
    for i, category in enumerate(categories):
        nodes.append({'name': category, 'category': 'category'})
        node_map[category] = len(sources) + i

    # 添加链接
    for _, row in category_source.iterrows():
        source_idx = node_map[row['来源']]
        category_idx = node_map[row['交易分类']]
        links.append({
            'source': source_idx,
            'target': category_idx,
            'value': float(row['金额'])
        })

    return {'nodes': nodes, 'links': links}


def analyze_engel_coefficient(df):
    """恩格尔系数：食品支出占比"""
    expense_df = df[df['收/支'] == '支出'].copy()

    total_expense = expense_df['金额'].sum()

    # 餐饮美食分类
    food_expense = expense_df[expense_df['交易分类'] == '餐饮美食']['金额'].sum()

    engel_coefficient = (food_expense / total_expense * 100) if total_expense > 0 else 0

    return {
        'coefficient': float(engel_coefficient),
        'food_expense': float(food_expense),
        'total_expense': float(total_expense),
        'level': '富裕' if engel_coefficient < 30 else '小康' if engel_coefficient < 40 else '温饱' if engel_coefficient < 50 else '贫困'
    }


def analyze_weekend_vs_monday(df):
    """周末与周一消费对比"""
    expense_df = df[df['收/支'] == '支出'].copy()

    expense_df['day_type'] = expense_df['交易时间'].dt.dayofweek.map(
        lambda x: '周末' if x in [5, 6] else ('周一' if x == 0 else '工作日')
    )

    day_stats = []
    for day_type, group in expense_df.groupby('day_type'):
        day_stats.append({
            'day': day_type,
            'amount': float(group['金额'].sum()),
            'count': len(group),
            'avg': float(group['金额'].mean())
        })

    return day_stats


def analyze_payment_methods(df):
    """支付方式分析"""
    expense_df = df[df['收/支'] == '支出'].copy()

    # 按来源统计（支付宝/微信）
    payment_stats = expense_df.groupby('来源')['金额'].agg(['sum', 'count']).round(2)

    result = []
    for payment_method in payment_stats.index:
        result.append({
            'method': payment_method,
            'amount': float(payment_stats.loc[payment_method, 'sum']),
            'count': int(payment_stats.loc[payment_method, 'count'])
        })

    return result


# ============ 银行卡维度 ============
BANK_BRAND = {
    '农业银行': ('农行', '#00843D'), '中国银行': ('中行', '#AE1E23'),
    '工商银行': ('工行', '#C7000B'), '建设银行': ('建行', '#004A98'),
    '招商银行': ('招行', '#C50A26'), '民生银行': ('民生', '#0E9347'),
    '交通银行': ('交行', '#003C7E'), '网商银行': ('网商', '#1677FF'),
    '邮政储蓄': ('邮储', '#00854A'), '光大银行': ('光大', '#5B2D8E'),
    '中信银行': ('中信', '#D7000F'), '宁波银行': ('宁波', '#C8161E'),
    '平安银行': ('平安', '#E60012'), '浦发银行': ('浦发', '#003B7E'),
}
DIGITAL_WALLET = {
    '花呗': ('花呗', '#1677FF'), '借呗': ('借呗', '#1677FF'),
    '账户余额': ('支付宝余额', '#1677FF'), '余额宝': ('余额宝', '#FFB300'),
    '零钱通': ('零钱通', '#07C160'), '零钱': ('微信零钱', '#07C160'),
}


def _extract_bank_brand(pay):
    """从 收/付款方式 文本中抽取 (短名, 展示标签, 品牌色)。"""
    import re
    raw = str(pay or '').strip()
    s = raw.split('&')[0].strip()
    if not s or s.lower() in ('nan', 'none', 'null', '/'):
        return ('其他', '其他/未知', '#9AA0A6')
    for kw, (short, color) in DIGITAL_WALLET.items():
        if kw in s:
            return (short, short, color)
    m = re.search(r'([一-龥]{2,}银行)', s)
    tail = re.search(r'\((\d{3,4})\)', raw)
    if m:
        bank = m.group(1)
        for k, (short, color) in BANK_BRAND.items():
            if k in bank or bank in k:
                ctype = '信用卡' if '信用卡' in s else ('储蓄卡' if ('储蓄卡' in s or '借记' in s) else '')
                label = f"{short}{ctype}({tail.group(1)})" if tail else f"{short}{ctype}"
                return (short, label, color)
        return (bank[:2], bank, '#5856D6')
    return (s[:6], s[:8], '#9AA0A6')


def analyze_bank_cards(df):
    """银行卡维度：按出资银行卡/钱包统计支出，附银行品牌色供前端图标。"""
    if '收/付款方式' not in df.columns:
        return []
    expense = df[df['收/支'] == '支出'].copy()
    if expense.empty:
        return []
    agg = {}
    for _, row in expense.iterrows():
        short, label, color = _extract_bank_brand(row.get('收/付款方式', ''))
        item = agg.setdefault(label, {'bank': short, 'label': label, 'color': color, 'amount': 0.0, 'count': 0})
        try:
            item['amount'] += float(row['金额'])
        except (TypeError, ValueError):
            continue
        item['count'] += 1
    out = sorted(agg.values(), key=lambda x: -x['amount'])
    for x in out:
        x['amount'] = round(x['amount'], 2)
    return out


def analyze_members(df):
    """成员维度：每个成员的支出/收入/转入/转出/笔数。颜色由 API 层按 members.json 附加。"""
    if '成员' not in df.columns:
        return []
    d = df[~df['是否退款'].fillna(False)] if '是否退款' in df.columns else df
    out = []
    for name, g in d.groupby('成员'):
        out.append({
            'member': str(name),
            'expense': round(float(g[g['收/支'] == '支出']['金额'].sum()), 2),
            'income': round(float(g[g['收/支'] == '收入']['金额'].sum()), 2),
            'transfer_in': round(float(g[g['收/支'] == '转入']['金额'].sum()), 2),
            'transfer_out': round(float(g[g['收/支'] == '转出']['金额'].sum()), 2),
            'count': int(len(g)),
        })
    out.sort(key=lambda x: -x['expense'])
    return out


# ============ 渠道分析（银行卡/储蓄·信用/支付宝/微信 多维） ============
# 电子钱包/虚拟账户识别规则（按特异性排序：长词在前，避免"余额宝/账户余额"被"余额"截胡）
_WALLET_RULES = [
    ('余利宝', '余利宝', '理财账户', '#FF9500'),
    ('网商银行', '网商银行', '储蓄卡', '#FF6A00'),
    ('余额宝', '余额宝', '理财账户', '#FFB300'),
    ('零钱通', '零钱通', '理财账户', '#2BA471'),
    ('花呗', '花呗', '信用账户', '#1677FF'),
    ('借呗', '借呗', '信用账户', '#1677FF'),
    ('账户余额', '支付宝余额', '余额账户', '#1677FF'),
    ('经营账户', '微信经营账户', '余额账户', '#07C160'),
    ('零钱', '微信零钱', '余额账户', '#07C160'),
    ('余额', '支付宝余额', '余额账户', '#1677FF'),
]

# 渠道大类（coarse group）→ 颜色（用于类型占比饼图等）
_GROUP_COLOR = {
    '信用卡': '#FF3B30', '储蓄卡': '#007AFF', '电子钱包': '#34C759',
    '银行卡': '#5856D6', '未标注': '#9AA0A6',
}

# 平台（来源）展示
_PLATFORM_META = {
    '支付宝': ('支付宝', '#1677FF'), '微信': ('微信', '#07C160'),
    '银行': ('银行直连', '#5B6B7B'), '示例数据': ('示例数据', '#8E8E93'),
}


def _bank_short_color(bankname):
    """中文银行全名 → (短名, 品牌色)。"""
    for k, (short, color) in BANK_BRAND.items():
        if k in bankname or bankname in k:
            return short, color
    return bankname.replace('银行', '') or bankname, '#5856D6'


def _channel_of(source, pay):
    """把 (来源, 收/付款方式) 归一为一个资金渠道。

    返回 dict: key(去重键)/label(展示)/kind(细类)/group(大类)/bank(短名)/card(后4位)/color。
    - 银行卡：按 银行+卡号 识别，并区分 储蓄卡/信用卡（银行对账单=储蓄账户）。
    - 电子钱包：余额宝/零钱通/花呗/借呗/支付宝余额/微信零钱/经营账户。
    - 同一张实体卡跨平台（支付宝/微信/银行直连）归并到同一渠道。
    """
    import re
    raw = str(pay or '').strip()
    s = raw.split('&')[0].strip()              # 去掉 &优惠/&立减/&福利金 等修饰
    low = s.lower()

    m = re.search(r'([一-龥]{2,}银行)', s)
    tail = re.search(r'\((\d{3,4})\)', raw)
    if m:
        short, color = _bank_short_color(m.group(1))
        card = tail.group(1) if tail else ''
        if '信用卡' in s:
            kind = '信用卡'
        elif ('储蓄卡' in s) or ('借记' in s):
            kind = '储蓄卡'
        elif str(source) == '银行':
            kind = '储蓄卡'                     # 银行对账单都是借记/储蓄账户
        else:
            kind = '银行卡'                     # 卡种未标注，二次合并时按同卡号修正
        ctp = '' if kind == '银行卡' else kind
        label = f"{short}{ctp}({card})" if card else f"{short}{ctp or '银行卡'}"
        return {'key': f"{short}|{card}|{kind}", 'label': label, 'kind': kind,
                'group': '银行卡', 'bank': short, 'card': card, 'color': color}

    if s and low not in ('nan', 'none', 'null', '/', '-'):
        for kw, name, kind, color in _WALLET_RULES:
            if kw in s:
                return {'key': f"wallet|{name}", 'label': name, 'kind': kind,
                        'group': '电子钱包', 'bank': name, 'card': '', 'color': color}

    plat = str(source) if str(source) in ('支付宝', '微信', '银行') else '其他'
    return {'key': f"未标注|{plat}", 'label': f"未标注（{plat}）", 'kind': '未标注',
            'group': '未标注', 'bank': plat, 'card': '', 'color': '#9AA0A6'}


# 细类 → 资金属性（信用 vs 储蓄/余额），供"信用 vs 储蓄"对比
_CREDIT_KINDS = {'信用卡', '信用账户'}
_DEBIT_KINDS = {'储蓄卡', '余额账户', '理财账户', '银行卡'}


def _build_channel_metas(df):
    """对 df 每行计算渠道元信息（含同卡号跨平台二次合并）。

    返回 (metas, meta_by_pair)：metas 为与 df 行顺序对齐的 dict 列表。
    供 analyze_channels（渠道分析页）与 get_transactions（交易明细"渠道"列/筛选）共用，保证口径一致。
    """
    pairs = df[['来源', '收/付款方式']].drop_duplicates()
    meta_by_pair = {}
    for _, r in pairs.iterrows():
        meta_by_pair[(r['来源'], str(r['收/付款方式']))] = _channel_of(r['来源'], r['收/付款方式'])
    # 二次合并：卡种未标注（银行卡）若同 (银行,卡号) 存在明确储蓄/信用，则归并
    typed = {}
    for meta in meta_by_pair.values():
        if meta['card'] and meta['kind'] in ('信用卡', '储蓄卡'):
            typed.setdefault((meta['bank'], meta['card']), meta)
    for meta in meta_by_pair.values():
        if meta['kind'] == '银行卡' and (meta['bank'], meta['card']) in typed:
            t = typed[(meta['bank'], meta['card'])]
            meta['kind'], meta['key'], meta['label'] = t['kind'], t['key'], t['label']
    metas = [meta_by_pair[(s, str(p))] for s, p in zip(df['来源'], df['收/付款方式'])]
    return metas, meta_by_pair


def analyze_channels(df):
    """渠道分析：按资金渠道（银行卡/储蓄·信用/钱包）与平台（支付宝/微信/银行）多维统计。"""
    empty = {'channels': [], 'platforms': [], 'kind_summary': [],
             'credit_debit': {}, 'monthly': {'months': [], 'series': []}, 'totals': {}}
    if df is None or df.empty or '收/付款方式' not in df.columns:
        return empty

    d = df.copy()
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    if d.empty:
        return empty

    # 1+2) 计算每行渠道元信息（含同卡号跨平台二次合并），与交易明细共用同一函数
    metas, meta_by_pair = _build_channel_metas(d)
    d['_ckey'] = [m['key'] for m in metas]
    d['_clabel'] = [m['label'] for m in metas]
    d['_ckind'] = [m['kind'] for m in metas]
    d['_cgroup'] = [m['group'] for m in metas]

    is_exp = d['收/支'] == '支出'
    total_expense = float(d[is_exp]['金额'].sum())

    def _split(g):
        return {
            'expense': round(float(g[g['收/支'] == '支出']['金额'].sum()), 2),
            'income': round(float(g[g['收/支'] == '收入']['金额'].sum()), 2),
            'transfer_in': round(float(g[g['收/支'] == '转入']['金额'].sum()), 2),
            'transfer_out': round(float(g[g['收/支'] == '转出']['金额'].sum()), 2),
            'internal': round(float(g[g['收/支'] == '不计收支']['金额'].sum()), 2),
        }

    # 3) 渠道（每张卡/钱包）
    channels = []
    for key, g in d.groupby('_ckey'):
        meta = meta_by_pair_lookup(meta_by_pair, g)
        sp = _split(g)
        ecount = int((g['收/支'] == '支出').sum())
        # 平台分布（该渠道在支付宝/微信/银行各花多少）
        pb = []
        for plat, pg in g.groupby('来源'):
            pb.append({'platform': str(plat),
                       'expense': round(float(pg[pg['收/支'] == '支出']['金额'].sum()), 2),
                       'count': int(len(pg))})
        pb.sort(key=lambda x: -x['expense'])
        # top3 消费分类
        eg = g[g['收/支'] == '支出']
        tc = []
        if not eg.empty:
            cg = eg.groupby('交易分类')['金额'].sum().sort_values(ascending=False).head(3)
            tc = [{'name': str(k), 'value': round(float(v), 2)} for k, v in cg.items()]
        dates = g['交易时间']
        channels.append({
            'key': key, 'label': meta['label'], 'kind': meta['kind'], 'group': meta['group'],
            'bank': meta['bank'], 'card': meta['card'], 'color': meta['color'],
            **sp,
            'count': int(len(g)), 'expense_count': ecount,
            'avg': round(sp['expense'] / ecount, 2) if ecount else 0,
            'expense_ratio': round(sp['expense'] / total_expense * 100, 1) if total_expense else 0,
            'first_date': dates.min().strftime('%Y-%m-%d'),
            'last_date': dates.max().strftime('%Y-%m-%d'),
            'active_days': int(dates.dt.date.nunique()),
            'platform_breakdown': pb,
            'top_categories': tc,
        })
    channels.sort(key=lambda x: -x['expense'])

    # 4) 平台维度
    platforms = []
    for plat, g in d.groupby('来源'):
        name, color = _PLATFORM_META.get(str(plat), (str(plat), '#8E8E93'))
        sp = _split(g)
        platforms.append({
            'platform': str(plat), 'name': name, 'color': color, **sp,
            'count': int(len(g)), 'expense_count': int((g['收/支'] == '支出').sum()),
            'expense_ratio': round(sp['expense'] / total_expense * 100, 1) if total_expense else 0,
            'card_count': int(g['_ckey'].nunique()),
        })
    platforms.sort(key=lambda x: -x['expense'])

    # 5) 类型（细类）占比 —— 基于支出
    kind_summary = []
    eg_all = d[is_exp]
    for kind, g in eg_all.groupby('_ckind'):
        amt = float(g['金额'].sum())
        kind_summary.append({
            'kind': str(kind), 'expense': round(amt, 2), 'count': int(len(g)),
            'ratio': round(amt / total_expense * 100, 1) if total_expense else 0,
            'color': _GROUP_COLOR.get(_KIND_GROUP.get(str(kind), str(kind)), '#9AA0A6'),
        })
    kind_summary.sort(key=lambda x: -x['expense'])

    # 6) 信用 vs 储蓄/余额 对比
    def _bucket(kinds):
        sub = eg_all[eg_all['_ckind'].isin(kinds)]
        cnt = int(len(sub))
        amt = float(sub['金额'].sum())
        return {'expense': round(amt, 2), 'count': cnt,
                'avg': round(amt / cnt, 2) if cnt else 0,
                'ratio': round(amt / total_expense * 100, 1) if total_expense else 0}
    credit_debit = {'credit': _bucket(_CREDIT_KINDS), 'debit': _bucket(_DEBIT_KINDS)}

    # 7) 月度 × 渠道 堆叠（支出，取支出 top6 渠道 + 其他）
    em = eg_all.copy()
    months, series = [], []
    if not em.empty:
        em['_m'] = em['交易时间'].dt.strftime('%Y-%m')
        months = sorted(em['_m'].unique().tolist())
        top_labels = [c['label'] for c in channels[:6]]
        color_of = {c['label']: c['color'] for c in channels}
        em['_grp'] = em['_clabel'].where(em['_clabel'].isin(top_labels), '其他')
        pivot = em.groupby(['_grp', '_m'])['金额'].sum()
        order = top_labels + (['其他'] if (em['_grp'] == '其他').any() else [])
        for lab in order:
            data = [round(float(pivot.get((lab, mth), 0.0)), 2) for mth in months]
            series.append({'label': lab, 'color': color_of.get(lab, '#9AA0A6'), 'data': data})

    totals = {
        'expense': round(total_expense, 2),
        'income': round(float(d[d['收/支'] == '收入']['金额'].sum()), 2),
        'channel_count': len(channels),
        'card_count': sum(1 for c in channels if c['group'] == '银行卡'),
        'wallet_count': sum(1 for c in channels if c['group'] == '电子钱包'),
        'platform_count': len(platforms),
    }

    return {'channels': channels, 'platforms': platforms, 'kind_summary': kind_summary,
            'credit_debit': credit_debit, 'monthly': {'months': months, 'series': series},
            'totals': totals}


# 细类 → 大类（用于颜色归并）
_KIND_GROUP = {
    '信用卡': '信用卡', '储蓄卡': '储蓄卡', '银行卡': '银行卡',
    '信用账户': '信用卡', '余额账户': '电子钱包', '理财账户': '电子钱包', '未标注': '未标注',
}


def meta_by_pair_lookup(meta_by_pair, g):
    """从分组首行取回（合并后的）渠道元信息。"""
    row = g.iloc[0]
    return meta_by_pair[(row['来源'], str(row['收/付款方式']))]


def generate_smart_tags(df):
    """生成智能标签（消费画像）"""
    expense_df = df[df['收/支'] == '支出'].copy()

    result = {
        'tags': [],
        'time_pattern': '-',
        'spending_preference': '-',
        'spending_pattern': '-',
        'spending_power': '-'
    }

    # 计算总体消费情况
    total_expense = expense_df['金额'].sum()
    avg_expense = expense_df['金额'].mean()
    daily_expense = expense_df.groupby(expense_df['交易时间'].dt.date)['金额'].sum().mean()

    # 时间模式分析
    hour_stats = expense_df.groupby(expense_df['交易时间'].dt.hour).size()
    peak_hours = hour_stats[hour_stats > hour_stats.mean()].index.tolist()

    if 22 in peak_hours or 23 in peak_hours or 0 in peak_hours:
        result['tags'].append('夜间消费达人')
        result['time_pattern'] = '您偏好在夜间消费，要注意作息哦'
    elif 6 in peak_hours or 7 in peak_hours:
        result['tags'].append('早起达人')
        result['time_pattern'] = '您是个早起消费的生活达人'
    else:
        result['time_pattern'] = '您的消费时间比较规律，集中在日间'

    # 消费偏好分析
    category_ratio = expense_df.groupby('交易分类')['金额'].sum() / total_expense
    top_categories = category_ratio[category_ratio > 0.15].index.tolist()

    preference_desc = []
    for category in top_categories:
        result['tags'].append(f'{category}控')
        preference_desc.append(f'{category}({(category_ratio[category]*100):.1f}%)')

    if preference_desc:
        result['spending_preference'] = f"最常消费的品类是{', '.join(preference_desc)}"
    else:
        result['spending_preference'] = '消费比较均衡'

    # 消费规律分析
    daily_expenses = expense_df.groupby(expense_df['交易时间'].dt.date)['金额'].sum()
    cv = daily_expenses.std() / daily_expenses.mean()

    if cv < 0.5:
        result['tags'].append('消费稳健派')
        result['spending_pattern'] = '您的消费非常有规律，是个理性消费者'
    elif cv < 0.8:
        result['tags'].append('平衡消费派')
        result['spending_pattern'] = '您的消费较为均衡，适度有波动'
    else:
        result['tags'].append('随性消费派')
        result['spending_pattern'] = '您的消费比较随性，波动较大'

    # 消费能力分析
    daily_avg = daily_expense if not pd.isna(daily_expense) else 0
    if daily_avg < 50:
        power_desc = f'日均消费{daily_avg:.0f}元，属于理性消费人群'
    elif daily_avg < 100:
        power_desc = f'日均消费{daily_avg:.0f}元，属于中等消费人群'
    else:
        power_desc = f'日均消费{daily_avg:.0f}元，属于高消费人群'
    result['spending_power'] = power_desc

    return result


def generate_story_data(df):
    """生成年度账单故事数据 (增强版)"""
    expense_df = df[df['收/支'] == '支出'].copy()

    if expense_df.empty:
        return None

    # 1. 最贵的一天
    daily_sum = expense_df.groupby(expense_df['交易时间'].dt.date)['金额'].sum()
    max_day = daily_sum.idxmax()
    max_day_amount = daily_sum.max()

    # 2. 消费最高的一个月
    monthly_sum = expense_df.groupby(expense_df['交易时间'].dt.to_period('M'))['金额'].sum()
    max_month = monthly_sum.idxmax()
    max_month_amount = monthly_sum.max()

    # 3. 最晚的一笔消费
    expense_df['time_only'] = expense_df['交易时间'].dt.time
    late_night_df = expense_df[(expense_df['交易时间'].dt.hour >= 0) & (expense_df['交易时间'].dt.hour <= 4)]
    if not late_night_df.empty:
        latest_tx = late_night_df.sort_values('time_only', ascending=False).iloc[0]
    else:
        latest_tx = expense_df.sort_values('time_only', ascending=False).iloc[0]

    # 4. 消费最多的分类
    top_cat = expense_df.groupby('交易分类')['金额'].sum().idxmax()
    top_cat_amount = expense_df.groupby('交易分类')['金额'].sum().max()

    # 5. 全年总览
    total_days = (expense_df['交易时间'].max() - expense_df['交易时间'].min()).days + 1
    total_tx_count = len(expense_df)

    # --- 新增：特色指数 ---

    # [咖啡指数]
    coffee_keywords = ['咖啡', 'luckin', 'starbucks', '瑞幸', '星巴克', 'manner', 'tim hortons', '皮爷']
    coffee_df = expense_df[expense_df['商品说明'].str.contains('|'.join(coffee_keywords), case=False, na=False) |
                           expense_df['交易对方'].str.contains('|'.join(coffee_keywords), case=False, na=False)]
    coffee_count = len(coffee_df)
    coffee_total = coffee_df['金额'].sum()

    # [深夜哲学] (22:00 - 05:00)
    night_philosophy_df = expense_df[(expense_df['交易时间'].dt.hour >= 22) | (expense_df['交易时间'].dt.hour <= 4)]
    night_avg = night_philosophy_df['金额'].mean() if not night_philosophy_df.empty else 0
    night_total = night_philosophy_df['金额'].sum()

    # [周末人格]
    expense_df['weekday'] = expense_df['交易时间'].dt.weekday  # 0=Mon, 6=Sun
    weekday_df = expense_df[expense_df['weekday'] < 5]
    weekend_df = expense_df[expense_df['weekday'] >= 5]

    weekday_avg = weekday_df['金额'].mean() if not weekday_df.empty else 0
    weekend_avg = weekend_df['金额'].mean() if not weekend_df.empty else 0

    # [通胀感知]
    # 找频率最高的商家
    top_merchant = expense_df['交易对方'].value_counts().idxmax()
    merchant_df = expense_df[expense_df['交易对方'] == top_merchant].sort_values('交易时间')

    inflation_data = {'merchant': top_merchant, 'start_price': 0, 'end_price': 0, 'trend': 'stable'}
    if len(merchant_df) > 5:
        # 取前3笔和后3笔的平均值比较
        start_price = merchant_df.head(3)['金额'].mean()
        end_price = merchant_df.tail(3)['金额'].mean()
        inflation_data['start_price'] = float(start_price)
        inflation_data['end_price'] = float(end_price)
        if end_price > start_price * 1.1:
            inflation_data['trend'] = 'up'
        elif end_price < start_price * 0.9:
            inflation_data['trend'] = 'down'

    # --- 新增 V2 (Rich Story) ---

    # 1. 年度首单
    first_tx = expense_df.sort_values('交易时间').iloc[0]

    # 2. 剁手黄金时间 (小时)
    peak_hour = expense_df['交易时间'].dt.hour.mode()[0]

    # 3. 外卖之王
    takeout_keywords = ['美团', '饿了么', '外卖', '肯德基', '麦当劳']
    takeout_df = expense_df[expense_df['商品说明'].str.contains('|'.join(takeout_keywords), case=False, na=False) |
                            expense_df['交易对方'].str.contains('|'.join(takeout_keywords), case=False, na=False)]
    takeout_count = len(takeout_df)
    takeout_amount = takeout_df['金额'].sum()

    # 4. 消费季节
    # 12-2 冬, 3-5 春, 6-8 夏, 9-11 秋
    def get_season(month):
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Autumn'

    expense_df['season'] = expense_df['交易时间'].dt.month.apply(get_season)
    season_result = expense_df.groupby('season')['金额'].sum()
    if not season_result.empty:
        top_season_en = season_result.idxmax()
        season_map = {'Winter': '冬', 'Spring': '春', 'Summer': '夏', 'Autumn': '秋'}
        top_season = season_map.get(top_season_en, '全年')
    else:
        top_season = '全年'

    return {
        'max_day': {
            'date': max_day.strftime('%Y年%m月%d日'),
            'amount': float(max_day_amount)
        },
        'max_month': {
            'month': str(max_month),
            'amount': float(max_month_amount)
        },
        'latest_tx': {
            'time': latest_tx['交易时间'].strftime('%H:%M'),
            'merchant': latest_tx['交易对方'],
            'amount': float(latest_tx['金额'])
        },
        'top_category': {
            'name': top_cat,
            'amount': float(top_cat_amount)
        },
        'summary': {
            'total_days': int(total_days),
            'tx_count': int(total_tx_count),
            'total_amount': float(expense_df['金额'].sum())
        },
        'features': {
            'coffee': {
                'count': int(coffee_count),
                'amount': float(coffee_total)
            },
            'night': {
                'avg': float(night_avg),
                'total': float(night_total),
                'count': len(night_philosophy_df)
            },
            'weekend': {
                'weekday_avg': float(weekday_avg),
                'weekend_avg': float(weekend_avg)
            },
            'inflation': inflation_data,
            'first_tx': {
                'date': first_tx['交易时间'].strftime('%Y-%m-%d %H:%M'),
                'merchant': first_tx['交易对方'],
                'amount': float(first_tx['金额']),
                'product': first_tx['商品说明']
            },
            'peak_hour': int(peak_hour),
            'takeout': {
                'count': int(takeout_count),
                'amount': float(takeout_amount)
            },
            'top_season': top_season
        }
    }


# ============ 辅助计算函数 ============

def calculate_monthly_stats(df):
    """计算月度统计数据"""
    if df.empty:
        return {
            'balance': 0,
            'total_expense': 0,
            'total_income': 0,
            'expense_count': 0,
            'income_count': 0,
            'total_count': 0,
            'active_days': 0,
            'avg_transaction': 0,
            'avg_daily_expense': 0,
            'expense_ratio': 0
        }

    expense_df = df[(df['收/支'] == '支出') & (~df['是否退款'])]
    income_df = df[(df['收/支'] == '收入') & (~df['是否退款'])]

    total_expense = expense_df['金额'].sum() if not expense_df.empty else 0
    total_income = income_df['金额'].sum() if not income_df.empty else 0
    active_days = len(df['日期'].unique())

    return {
        'balance': total_income - total_expense,
        'total_expense': total_expense,
        'total_income': total_income,
        'expense_count': len(expense_df),
        'income_count': len(income_df),
        'total_count': len(expense_df) + len(income_df),
        'active_days': active_days,
        'avg_transaction': round(expense_df['金额'].mean(), 2) if len(expense_df) > 0 else 0,
        'avg_daily_expense': round(total_expense / max(1, active_days), 2),
        'expense_ratio': round(total_expense / total_income * 100, 2) if total_income > 0 else 0
    }


def calculate_yearly_stats(df):
    """计算年度统计数据"""
    return calculate_monthly_stats(df)  # 使用相同的统计逻辑


def calculate_change_rate(current, previous):
    """计算环比变化率，处理特殊情况"""
    try:
        if previous == 0:
            if current == 0:
                return 0
            return None
        if current == 0:
            return -100
        return round((current - previous) / abs(previous) * 100, 2)
    except:
        return None
