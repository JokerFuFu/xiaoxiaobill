"""
资产负债(净资产)服务 —— 三表模型中的「资产负债表」。

核心理念:资产是存量,流水是流量;流水永远推不出净资产,必须靠「余额快照」。
- 账户:用户自己的资金容器(储蓄卡/信用卡/支付宝/微信/投资/现金/其他)。
- 快照:某一天各账户的余额(信用卡填欠款额,系统按负债处理)。
- 趋势:净资产 = 资产合计 - 负债合计,随快照时间序列变化。
- 解释:相邻两次快照之间,用流水的「资金性质」口径解释净资产变化:
    Δ净资产 ≈ 真实收入 - 真实消费 + 往来净额 + 退款报销 + (投资损益及未解释项)
  最后一项是推算余项 —— 它把"投资涨跌 + 现金交易 + 漏记账"显性化,而不是假装不存在。

数据存 upload/<uid>/_accounts.json / _balance_snapshots.json (0600)。
"""
import json
import logging
import os
import secrets
import threading

from config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)
_nw_lock = threading.RLock()

# 账户类型;负债类账户余额按"欠款额"录入,计算净资产时取负
ACCOUNT_TYPES = ['储蓄卡', '信用卡', '支付宝', '微信', '投资', '现金', '其他资产', '其他负债']
LIABILITY_TYPES = {'信用卡', '其他负债'}
MAX_ACCOUNTS = 50
MAX_SNAPSHOTS = 500


def _path(uid, name):
    return os.path.join(UPLOAD_FOLDER, uid, name)


def _load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f) or default
    except Exception:
        logger.exception(f"读取 {path} 失败")
    return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


# ============ 账户 ============
def list_accounts(uid):
    return _load_json(_path(uid, '_accounts.json'), [])


def add_account(uid, name, type_):
    name = str(name or '').strip()[:24]
    if not name:
        raise ValueError('账户名不能为空')
    if type_ not in ACCOUNT_TYPES:
        raise ValueError('未知账户类型')
    with _nw_lock:
        accounts = list_accounts(uid)
        if len(accounts) >= MAX_ACCOUNTS:
            raise ValueError(f'账户最多 {MAX_ACCOUNTS} 个')
        if any(a['name'] == name for a in accounts):
            raise ValueError('账户名已存在')
        acc = {'id': 'a' + secrets.token_hex(4), 'name': name, 'type': type_}
        accounts.append(acc)
        _save_json(_path(uid, '_accounts.json'), accounts)
        return acc


def update_account(uid, aid, name=None, type_=None):
    with _nw_lock:
        accounts = list_accounts(uid)
        acc = next((a for a in accounts if a['id'] == aid), None)
        if not acc:
            raise ValueError('账户不存在')
        if name is not None and str(name).strip():
            acc['name'] = str(name).strip()[:24]
        if type_ is not None:
            if type_ not in ACCOUNT_TYPES:
                raise ValueError('未知账户类型')
            acc['type'] = type_
        _save_json(_path(uid, '_accounts.json'), accounts)
        return acc


def delete_account(uid, aid):
    with _nw_lock:
        accounts = [a for a in list_accounts(uid) if a['id'] != aid]
        _save_json(_path(uid, '_accounts.json'), accounts)
        # 同时从所有快照里移除该账户的余额
        snaps = list_snapshots(uid)
        for s in snaps:
            s.get('balances', {}).pop(aid, None)
        _save_json(_path(uid, '_balance_snapshots.json'), snaps)
        return accounts


# ============ 快照 ============
def list_snapshots(uid):
    snaps = _load_json(_path(uid, '_balance_snapshots.json'), [])
    snaps.sort(key=lambda s: s.get('date', ''))
    return snaps


def upsert_snapshot(uid, date, balances, note=''):
    """按日期 upsert 一条快照。balances: {account_id: number(信用卡填欠款正数,按当日日终余额)}。"""
    import math
    from datetime import date as _date
    date = str(date or '').strip()[:10]
    try:
        _date.fromisoformat(date)   # 严格校验,垃圾日期会让后续 explain 永久 500
    except (TypeError, ValueError):
        raise ValueError('日期格式应为 YYYY-MM-DD')
    if not isinstance(balances, dict) or not balances:
        raise ValueError('至少填写一个账户余额')
    with _nw_lock:
        accounts = {a['id'] for a in list_accounts(uid)}
        clean = {}
        for aid, v in balances.items():
            if aid not in accounts:
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(f) or abs(f) > 1e13:   # 拒绝 NaN/Inf/天文数字(会产生非法 JSON)
                continue
            clean[aid] = round(f, 2)
        if not clean:
            raise ValueError('没有有效的余额数据')
        snaps = list_snapshots(uid)
        if len(snaps) >= MAX_SNAPSHOTS and not any(s['date'] == date for s in snaps):
            raise ValueError(f'快照最多 {MAX_SNAPSHOTS} 条')
        existing = next((s for s in snaps if s.get('date') == date), None)
        if existing:
            existing['balances'] = clean
            existing['note'] = str(note or '')[:100]
        else:
            snaps.append({'date': date, 'balances': clean, 'note': str(note or '')[:100]})
        snaps.sort(key=lambda s: s['date'])
        _save_json(_path(uid, '_balance_snapshots.json'), snaps)
        return snaps


def delete_snapshot(uid, date):
    with _nw_lock:
        snaps = [s for s in list_snapshots(uid) if s.get('date') != date]
        _save_json(_path(uid, '_balance_snapshots.json'), snaps)
        return snaps


# ============ 计算 ============
def _signed(acc_type, value):
    return -abs(value) if acc_type in LIABILITY_TYPES else value


def trend(uid):
    """[{date, net, assets, liabilities, by_type:{类型: 合计(负债为负)}}] 按时间升序。"""
    accounts = {a['id']: a for a in list_accounts(uid)}
    out = []
    for s in list_snapshots(uid):
        by_type, assets, liabilities = {}, 0.0, 0.0
        for aid, v in (s.get('balances') or {}).items():
            acc = accounts.get(aid)
            if not acc:
                continue
            sv = _signed(acc['type'], float(v))
            by_type[acc['type']] = round(by_type.get(acc['type'], 0.0) + sv, 2)
            if sv >= 0:
                assets += sv
            else:
                liabilities += -sv
        out.append({'date': s['date'], 'net': round(assets - liabilities, 2),
                    'assets': round(assets, 2), 'liabilities': round(liabilities, 2),
                    'by_type': by_type, 'note': s.get('note', '')})
    return out


def explain(uid, df=None):
    """相邻快照间的净资产变化 vs 流水口径解释。df 为带「资金性质」列的全量流水(可为 None)。"""
    t = trend(uid)
    if len(t) < 2:
        return []
    rows = []
    for prev, cur in zip(t, t[1:]):
        delta = round(cur['net'] - prev['net'], 2)
        item = {'from': prev['date'], 'to': cur['date'], 'delta_net': delta,
                'income': None, 'expense': None, 'transfer_net': None,
                'refund_reimburse': None, 'residual': None}
        if df is not None and len(df) and '资金性质' in df.columns:
            import pandas as pd
            try:
                # 快照=当日日终余额 → 区间取 (prev日终, cur日终]:从 prev 次日 00:00 起算
                lo = pd.Timestamp(prev['date']) + pd.Timedelta(days=1)
                hi = pd.Timestamp(cur['date']) + pd.Timedelta(days=1)
            except (ValueError, TypeError):
                rows.append(item)   # 历史脏日期:跳过流水解释,不让整页 500
                continue
            d = df[(df['交易时间'] >= lo) & (df['交易时间'] < hi)]
            if '是否退款' in d.columns:
                d = d[~d['是否退款'].fillna(False)]
            nat = d.groupby('资金性质')['金额'].sum()

            def g(*names):
                return round(float(sum(nat.get(n, 0.0) for n in names)), 2)

            income = g('工资收入', '投资收益', '其他收入')
            expense = g('消费')
            t_in = float(d[(d['资金性质'] == '转账往来') & (d['收/支'].isin(['收入', '转入']))]['金额'].sum())
            t_out = float(d[(d['资金性质'] == '转账往来') & (d['收/支'].isin(['支出', '转出']))]['金额'].sum())
            rr = g('退款', '报销')
            expected = income - expense + (t_in - t_out) + rr
            item.update({'income': income, 'expense': expense,
                         'transfer_net': round(t_in - t_out, 2),
                         'refund_reimburse': rr,
                         'residual': round(delta - expected, 2)})
        rows.append(item)
    rows.reverse()   # 最近的在前
    return rows
