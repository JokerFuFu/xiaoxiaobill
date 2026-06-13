"""
预算管理服务 —— 给消费记录加上「目标」这条线。

设计:一套「按月循环」的预算(每月都适用),含总预算 + 可选的分类预算。
口径与全站一致:花了多少 = 资金性质「消费」(真实消费,不含转账/还款/投资)。
状态计算给出:已花/剩余/进度、按当前节奏预测的月末总额(burn-rate)、超支分类。

存 upload/<uid>/_budget.json(无敏感信息,0600 与其它一致)。
"""
import json
import logging
import os
import threading
from calendar import monthrange
from datetime import datetime

from config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)
_b_lock = threading.RLock()

MAX_CATEGORIES = 40


def _path(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_budget.json')


def get_budget(uid):
    try:
        p = _path(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                d = json.load(f) or {}
                return {
                    'monthly_total': d.get('monthly_total'),
                    'categories': d.get('categories') or {},
                    'updated': d.get('updated', ''),
                }
    except Exception:
        logger.exception("读取预算失败")
    return {'monthly_total': None, 'categories': {}, 'updated': ''}


def save_budget(uid, monthly_total=None, categories=None):
    with _b_lock:
        def _num(v):
            try:
                f = float(v)
                return round(f, 2) if f > 0 else None
            except (TypeError, ValueError):
                return None

        cats = {}
        if isinstance(categories, dict):
            for k, v in list(categories.items())[:MAX_CATEGORIES]:
                amt = _num(v)
                name = str(k).strip()[:30]
                if name and amt:
                    cats[name] = amt
        new = {
            'monthly_total': _num(monthly_total),
            'categories': cats,
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        p = _path(uid)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(new, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
        try:
            os.chmod(p, 0o600)
        except Exception:
            pass
        return new


def _real_expense(df, year, month):
    """该月真实消费明细(资金性质=消费,去退款)。返回 (总额, 按分类Series)。"""
    import pandas as pd
    d = df
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    if '资金性质' in d.columns:
        d = d[d['资金性质'] == '消费']
    else:
        d = d[d['收/支'] == '支出']
    d = d[(d['交易时间'].dt.year == year) & (d['交易时间'].dt.month == month)]
    if d.empty:
        return 0.0, pd.Series(dtype=float)
    by_cat = d.groupby('交易分类')['金额'].sum().sort_values(ascending=False)
    return round(float(d['金额'].sum()), 2), by_cat


def status(uid, df, year=None, month=None):
    """某月预算执行情况。"""
    now = datetime.now()
    year = int(year or now.year)
    month = int(month or now.month)
    bud = get_budget(uid)
    total_spent, by_cat = _real_expense(df, year, month)

    days_in_month = monthrange(year, month)[1]
    if (year, month) == (now.year, now.month):
        day_elapsed = now.day
    elif (year, month) < (now.year, now.month):
        day_elapsed = days_in_month        # 过去的月份已走完
    else:
        day_elapsed = 0                     # 未来月份
    day_elapsed = max(1, min(day_elapsed, days_in_month))

    def _proj(spent):
        # 按当前日均推算月末(仅当月有意义;历史月直接=已花)
        if (year, month) >= (now.year, now.month) and day_elapsed < days_in_month:
            return round(spent / day_elapsed * days_in_month, 2)
        return round(spent, 2)

    total = bud.get('monthly_total')
    out = {
        'year': year, 'month': month,
        'days_in_month': days_in_month, 'day_elapsed': day_elapsed,
        'has_budget': bool(total) or bool(bud.get('categories')),
        'total_budget': total,
        'total_spent': total_spent,
        'total_remaining': round(total - total_spent, 2) if total else None,
        'total_pct': round(total_spent / total * 100, 1) if total else None,
        'projected': _proj(total_spent),
        'projected_over': bool(total and _proj(total_spent) > total),
        'categories': [],
    }
    cat_budgets = bud.get('categories') or {}
    for cat, b in sorted(cat_budgets.items(), key=lambda kv: -kv[1]):
        spent = round(float(by_cat.get(cat, 0.0)), 2)
        out['categories'].append({
            'category': cat, 'budget': b, 'spent': spent,
            'remaining': round(b - spent, 2),
            'pct': round(spent / b * 100, 1) if b else None,
            'over': spent > b,
        })
    # 没设分类预算时,给出本月消费 top 分类供用户参考/快速设预算
    if not cat_budgets:
        out['top_categories'] = [{'category': str(k), 'spent': round(float(v), 2)}
                                 for k, v in by_cat.head(8).items()]
    return out
