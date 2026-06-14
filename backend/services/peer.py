"""
个人往来对账 —— 看你和某个人之间的钱怎么走的(转入/转出/净额),代付/借还一目了然。

场景:给某人代充 AI 订阅、帮人垫付后对方再转你、亲友间借还。这些都散在转账记录里,
单看每笔看不出"谁欠谁"。这里按对手方汇总:总转入 vs 总转出 = 净额。

只挑"个人"对手方(至少有一笔资金性质=转账往来),避免把商户也算进来。
大额(≥1万)与日常分开统计,免得几笔大额资金搬运盖过日常的代付/报销。
"""
import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

_BIG = 10000   # 大额阈值:区分"资金搬运"与"日常往来/代付"
# 商户/机构后缀:这些不是"个人",从往来对账里剔除
_MERCHANT_RE = re.compile(r'店|公司|商城|超市|平台|旗舰|科技|有限|集团|银行|基金|证券|购物金|官方|客服|小店')


def _is_person_counterparties(df):
    """返回有过『转账往来』的对手方集合(视为个人);剔除明显的商户/机构名。"""
    if '资金性质' not in df.columns:
        return set()
    tr = df[df['资金性质'] == '转账往来']
    return set(p for p in tr['交易对方'].astype(str).unique()
               if p and p != 'nan' and len(p) > 1 and not _MERCHANT_RE.search(p))


def _self_names(uid):
    """账户持有人本人的名字(用于剔除账户间自转,不算个人往来)。"""
    names = set()
    try:
        from services import auth as auth_svc
        u = auth_svc.get_user(uid) if uid else None
        if u and u.display_name and u.display_name not in ('管理员', 'admin'):
            names.add(u.display_name)
    except Exception:
        pass
    return names


def _make_is_self(self_names):
    def is_self(p):
        pp = p.replace('*', '').strip()
        for nm in self_names:
            if not nm:
                continue
            if p == nm or (pp and len(pp) >= 2 and (pp in nm or nm.endswith(pp) or nm.startswith(pp))):
                return True
        return False
    return is_self


def peer_transfers(df, uid=None, top=15, name=None):
    out = {'peers': [], 'queried': name}
    if df is None or len(df) == 0:
        return out
    persons = _is_person_counterparties(df)
    if not persons:
        return out
    is_self = _make_is_self(_self_names(uid))
    persons = {p for p in persons if not is_self(p)}    # 剔除本人账户间自转
    if not persons:
        return out
    d = df.copy()
    d['_p'] = d['交易对方'].astype(str)
    d = d[d['_p'].isin(persons)]
    if name:
        d = d[d['_p'].str.contains(name, na=False)]
    if d.empty:
        return out

    is_in = d['收/支'].isin(['收入', '转入'])
    is_out = d['收/支'].isin(['支出', '转出'])
    peers = []
    for p, g in d.groupby('_p'):
        gin = g[g['收/支'].isin(['收入', '转入'])]
        gout = g[g['收/支'].isin(['支出', '转出'])]
        in_t = float(gin['金额'].sum())
        out_t = float(gout['金额'].sum())
        big_in = float(gin[gin['金额'] >= _BIG]['金额'].sum())
        big_out = float(gout[gout['金额'] >= _BIG]['金额'].sum())
        recent = []
        for _, r in g.sort_values('交易时间', ascending=False).head(12).iterrows():
            recent.append({
                'date': r['交易时间'].strftime('%Y-%m-%d'),
                'dir': r['收/支'],
                'amount': round(float(r['金额']), 2),
                'nature': str(r.get('资金性质', '')),
                'desc': str(r.get('商品说明', '') or '')[:40],
            })
        peers.append({
            'name': p[:40], 'count': int(len(g)),
            'in_total': round(in_t, 2), 'out_total': round(out_t, 2),
            'net': round(in_t - out_t, 2),
            'daily_in': round(in_t - big_in, 2), 'daily_out': round(out_t - big_out, 2),
            'daily_net': round((in_t - big_in) - (out_t - big_out), 2),
            'big_in': round(big_in, 2), 'big_out': round(big_out, 2),
            'first': g['交易时间'].min().strftime('%Y-%m-%d'),
            'last': g['交易时间'].max().strftime('%Y-%m-%d'),
            'recent': recent,
        })
    # 按往来总量排序(日常优先体现,大额单列)
    peers.sort(key=lambda x: -(abs(x['in_total']) + abs(x['out_total'])))
    out['peers'] = peers if name else peers[:top]
    return out
