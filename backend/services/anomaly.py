"""
异常消费提醒 —— 在真实消费里自动揪出"不对劲"的支出,主动提醒。

检测四类(都基于用户自身历史做基线,不用拍脑袋的绝对阈值):
  ① 大额离群:单笔金额远超个人日常(> P97 且 > 中位数×5)。
  ② 分类激增:某分类本月支出 ≫ 前 3 个月均值(≥2 倍且绝对额显著)。
  ③ 疑似重复扣费:同日同对手方同金额多笔(可能误扣/重复下单)。
  ④ 月度激增:本月真实消费总额 ≫ 近 6 个月均值。
锚定"最近有数据的月份"为本月。返回按严重度排序的提醒列表。
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


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


def detect(df, limit=20):
    con = _real_consumption(df)
    if con is None or len(con) == 0:
        return {'count': 0, 'anchor_month': None, 'alerts': []}
    con = con.copy()
    con['_m'] = con['交易时间'].dt.strftime('%Y-%m')
    con['金额'] = con['金额'].astype(float)
    anchor = con['_m'].max()                       # 最近有数据的月份 = "本月"
    alerts = []

    # ① 大额离群(全期)。排除房租等"本就该大额且固定"的类目,按(对手方+金额)去重避免房租刷屏
    amts = con['金额']
    p97 = amts.quantile(0.97)
    med = amts.median()
    thr = max(p97, med * 5, 500)
    big_pool = con[(con['金额'] >= thr) & (~con['交易分类'].astype(str).isin(['住房', '信用卡还款']))]
    big_pool = big_pool.sort_values('交易时间', ascending=False)
    seen_big = set()
    for _, r in big_pool.iterrows():
        key = (str(r.get('交易对方', '')), round(float(r['金额']), 0))
        if key in seen_big:
            continue
        seen_big.add(key)
        ratio = r['金额'] / med if med else 0
        alerts.append({
            'type': 'big', 'severity': min(99, int(ratio)),
            'title': f"大额支出 ¥{r['金额']:.0f}",
            'detail': f"{r['_m']} · {str(r.get('交易分类',''))} · {str(r.get('交易对方','') or r.get('商品说明',''))[:24]}（约为你单笔中位数的 {ratio:.0f} 倍）",
            'amount': round(float(r['金额']), 2), 'date': r['交易时间'].strftime('%Y-%m-%d'),
        })
        if len(seen_big) >= 6:
            break

    # ② 分类激增(本月 vs 前3月均值)
    cur = con[con['_m'] == anchor]
    months_sorted = sorted(con['_m'].unique())
    prev3 = months_sorted[-4:-1] if len(months_sorted) >= 2 else []
    if prev3:
        cur_cat = cur.groupby('交易分类')['金额'].sum()
        base = con[con['_m'].isin(prev3)].groupby('交易分类')['金额'].sum() / len(prev3)
        for cat, cv in cur_cat.items():
            bv = float(base.get(cat, 0))
            if cv >= 300 and (bv == 0 or cv >= bv * 2) and cv - bv >= 200:
                times = (cv / bv) if bv else 0
                alerts.append({
                    'type': 'cat_spike', 'severity': int(min(90, (times or 5) * 10)),
                    'title': f"「{cat}」本月激增",
                    'detail': (f"本月 ¥{cv:.0f}，前3月均值 ¥{bv:.0f}" + (f"（≈{times:.1f} 倍）" if bv else "（前3月几乎没花）")),
                    'amount': round(float(cv), 2), 'date': anchor,
                })

    # ③ 同日多笔同额:可能误扣/重复下单。排除税务/社保/缴费等"批量代缴"(同日多笔是正常的)
    import re as _re
    _BATCH = _re.compile(r'税务|社保|医保|公积金|缴费|党费|工会')
    con['_day'] = con['交易时间'].dt.strftime('%Y-%m-%d')
    con['_party'] = con['交易对方'].astype(str).fillna('')
    dup = con.groupby(['_day', '_party', '金额']).size()
    for (day, party, amt), n in dup[dup >= 2].items():
        if amt < 30 or not party.strip() or party in ('nan', ''):
            continue
        if _BATCH.search(party):
            continue
        alerts.append({
            'type': 'dup', 'severity': 55 + int(n) + (10 if amt >= 500 else 0),
            'title': f"同日 {n} 笔同额支出",
            'detail': f"{day} · {party[:24]} · 同金额 ¥{amt:.2f} 当日 {n} 笔，留意是否重复",
            'amount': round(float(amt) * n, 2), 'date': day,
        })

    # ④ 月度激增(本月 vs 近6月均值)
    monthly = con.groupby('_m')['金额'].sum()
    if len(monthly) >= 3:
        cur_total = float(monthly.get(anchor, 0))
        hist = monthly[monthly.index < anchor].tail(6)
        base = float(hist.mean()) if len(hist) else 0
        if base and cur_total >= base * 1.5 and cur_total - base >= 1000:
            alerts.append({
                'type': 'month_spike', 'severity': int(min(95, cur_total / base * 30)),
                'title': f"本月消费偏高",
                'detail': f"{anchor} 真实消费 ¥{cur_total:.0f}，近6月均值 ¥{base:.0f}（高 {(cur_total/base-1)*100:.0f}%）",
                'amount': round(cur_total, 2), 'date': anchor,
            })

    alerts.sort(key=lambda x: -x['severity'])
    return {'count': len(alerts), 'anchor_month': anchor, 'alerts': alerts[:limit]}
