"""
订阅 / 定期扣费识别 —— 找出每月(或每季/每年)规律重复的固定支出。

定期扣费 = 同一对手方、按固定周期、金额稳定地反复扣。覆盖:会员订阅(视频/音乐/云/软件)、
公共事业(水电燃气宽带话费)、房租物业、保险、税费等。不是"高频商户"(那是吃饭/网购,金额跳)。

判定(在真实消费里):同一交易对方 ≥3 次且跨 ≥3 个不同月份,且满足其一:
  ① 金额稳定(变异系数 cv<0.25) 且 间隔接近月/季/年;
  ② 命中订阅关键词(自动续费/连续包月/会员/Apple/Netflix… 这类即便金额略变也算)。
高频但金额乱跳又无关键词的(淘宝/麦当劳)被排除。
"""
import logging
import re
from statistics import median

import pandas as pd

logger = logging.getLogger(__name__)

# 关键词 → 类型(命中即视为订阅/账单类)。顺序即优先级:税费/公共事业 先于 保险(税务局代缴医保别误判保险)
_TYPE_RULES = [
    ('订阅会员', re.compile(
        r'自动续费|连续包月|连续包年|续订|包月|包年|VIP|会员费|视频会员|音乐会员|网盘|云空间|iCloud|'
        r'Apple|App\s*Store|Netflix|Spotify|YouTube|腾讯视频|爱奇艺|优酷|芒果\s*TV|哔哩哔哩|网易云音乐|'
        r'百度网盘|阿里云盘|夸克网盘|Adobe|Notion|ChatGPT|OpenAI|Office\s*365|Microsoft\s*365|Steam|PlayStation|Linear', re.I)),
    ('税费', re.compile(r'税务局|个税|社保|社会保险|公积金|医保')),
    ('公共事业', re.compile(
        r'电力|供电|自来水|水务|燃气|天然气|话费|流量|宽带|物业|移动|联通|电信|广电|国网')),
    ('房租物业', re.compile(r'房租|租金|公寓|长租')),
    ('保险', re.compile(r'保险|保费|人寿|财险|健康险|重疾')),
]
# 交易分类 → 类型(对手方无关键词时,用账单自带分类兜底归类)
_CAT_TYPE = [('房租物业', ('住房',)), ('公共事业', ('生活缴费', '缴费', '通讯', '通信')),
             ('保险', ('保险',)), ('订阅会员', ('充值', '会员'))]
# 这些是"消费"类目(吃饭/购物),无订阅关键词时不当成定期扣费——常被高频规律误伤(食堂/常去餐厅)
_CONSUMPTION_CATS = ('餐饮美食', '美食', '日用百货', '服饰装扮', '数码电器', '母婴亲子',
                     '美容美发', '商户消费', '超市便利', '运动户外', '生鲜果蔬', '酒店旅游', '交通出行')


def _classify(text, cat=''):
    for name, pat in _TYPE_RULES:
        if pat.search(text):
            return name
    for name, cats in _CAT_TYPE:
        if any(c in cat for c in cats):
            return name
    return None


def _real_consumption(df):
    from services.nature import NATURE_COL, EXPENSE_NATURE
    if df is None or len(df) == 0:
        return df
    if NATURE_COL in df.columns:
        d = df[df[NATURE_COL] == EXPENSE_NATURE].copy()
    else:
        d = df[df['收/支'] == '支出'].copy()
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d


def _cadence(days_sorted):
    """由相邻间隔中位数判断周期。返回 (标签, 月频次, 中位间隔天)。"""
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


def detect(df, year=None):
    """识别订阅/定期扣费。year 只用于过滤展示口径外的统计;判定用全历史更稳。"""
    con = _real_consumption(df)
    out = {'count': 0, 'monthly_total': 0.0, 'annual_total': 0.0, 'items': [], 'by_type': []}
    if con is None or len(con) == 0:
        return out
    con = con.copy()
    con['_party'] = con['交易对方'].astype(str).fillna('').str.strip()
    con = con[con['_party'].str.len() > 1]

    items = []
    for party, g in con.groupby('_party'):
        if len(g) < 3:
            continue
        # 打码个人名(如 t***8 / lx**4)=对个人的转账,绝不是订阅商户,直接排除
        if '*' in party:
            continue
        g = g.sort_values('交易时间')
        months = g['交易时间'].dt.strftime('%Y-%m').nunique()
        if months < 3:
            continue
        amts = g['金额'].astype(float)
        mean_amt = amts.mean()
        cv = (amts.std() / mean_amt) if mean_amt else 9
        cat = str(g['交易分类'].mode().iloc[0]) if '交易分类' in g.columns and len(g) else ''
        text = party + ' ' + ' '.join(g['商品说明'].astype(str).head(5).tolist())
        ttype = _classify(text, cat)
        label, per_month, gap = _cadence(list(g['交易时间']))

        regular = label in ('每月', '每两周', '每季', '每半年', '每年')
        stable = cv < 0.25
        if ttype:
            # 有类型(关键词/账单分类):要求有规律 或 金额稳定,排除"高频又乱跳"的购物(如山姆会员商店)
            if not (regular or stable):
                continue
        else:
            # 无任何线索:必须既规律又稳定;且不在"吃饭/购物"消费类目里(避免食堂/常去店误判)
            if not (regular and stable):
                continue
            if any(c in cat for c in _CONSUMPTION_CATS):
                continue
            ttype = '其他定期'

        med_amt = round(float(amts.median()), 2)
        monthly_cost = round(med_amt * per_month, 2) if per_month else med_amt
        last = g['交易时间'].max()
        next_due = (last + pd.Timedelta(days=int(gap))).strftime('%Y-%m-%d') if gap else None
        items.append({
            'merchant': party[:40], 'type': ttype, 'cadence': label,
            'amount': med_amt, 'monthly_cost': monthly_cost, 'annual_cost': round(monthly_cost * 12, 2),
            'count': int(len(g)), 'months': int(months), 'cv': round(float(cv), 2),
            'last_date': last.strftime('%Y-%m-%d'), 'next_due': next_due,
            'total_paid': round(float(amts.sum()), 2),
            'sample': str(g['商品说明'].iloc[-1])[:40],
        })

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
