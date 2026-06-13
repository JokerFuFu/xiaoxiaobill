"""
年度账单报告 —— 把一年的钱浓缩成一张可分享的"年度账单"(类 Spotify Wrapped)。

数据与文案分离:
- build_data(df, uid, year):纯统计(真实消费/收入/结余、逐月、top分类、最大单笔、消费画像、
  订阅/境外/异常/净资产摘要),不依赖 AI → 没配 AI 也能看图看数。
- narrative(uid, df, year):把 build_data 的紧凑版交给模型写一段温度感的年度小结(只解读不编数),缓存。
"""
import json
import logging
import os
from datetime import datetime

import pandas as pd

from config import UPLOAD_FOLDER
from services import ai as ai_svc

logger = logging.getLogger(__name__)

_WEEKDAY = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']


def _r(v, n=2):
    try:
        return round(float(v), n)
    except Exception:
        return 0.0


def _real_consumption(df):
    from services.nature import NATURE_COL, EXPENSE_NATURE
    if NATURE_COL in df.columns:
        d = df[df[NATURE_COL] == EXPENSE_NATURE].copy()
    else:
        d = df[df['收/支'] == '支出'].copy()
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d


def available_years(df):
    if df is None or len(df) == 0:
        return []
    return sorted(df['交易时间'].dt.year.dropna().unique().astype(int).tolist())


def build_data(df, uid, year=None):
    """构造年度账单的结构化数据(无 AI)。"""
    years = available_years(df)
    if not years:
        return {'empty': True, 'years': []}
    year = int(year) if year else years[-1]
    con = _real_consumption(df)
    con = con[con['交易时间'].dt.year == year].copy()

    from services.income import overview as income_overview
    inc = income_overview(df, year) or {}
    real_income = inc.get('real_income', 0)
    real_expense = _r(con['金额'].sum())

    data = {
        'empty': len(con) == 0, 'year': year, 'years': years,
        'real_expense': real_expense,
        'real_income': _r(real_income),
        'saving': _r(real_income - real_expense),
        'saving_rate': inc.get('saving_rate'),
        'tx_count': int(len(con)),
    }
    if len(con) == 0:
        return data

    # 逐月消费
    mtrend = con.groupby(con['交易时间'].dt.month)['金额'].sum()
    data['monthly'] = [{'month': int(m), 'amount': _r(v)} for m, v in mtrend.items()]
    peak_m = mtrend.idxmax()
    data['peak_month'] = {'month': int(peak_m), 'amount': _r(mtrend.max())}

    # top 分类
    cg = con.groupby('交易分类')['金额'].agg(['sum', 'count']).sort_values('sum', ascending=False).head(10)
    data['top_categories'] = [{'category': str(k), 'amount': _r(r['sum']), 'count': int(r['count'])}
                              for k, r in cg.iterrows()]

    # 最大单笔
    big = con.sort_values('金额', ascending=False).head(5)
    data['biggest'] = [{'date': r['交易时间'].strftime('%Y-%m-%d'), 'amount': _r(r['金额']),
                        'category': str(r.get('交易分类', '')),
                        'desc': str(r.get('交易对方', '') or r.get('商品说明', ''))[:30]}
                       for _, r in big.iterrows()]

    # 消费画像
    active_days = con['交易时间'].dt.strftime('%Y-%m-%d').nunique()
    wk = con.groupby(con['交易时间'].dt.dayofweek)['金额'].sum()
    # 时段只用支付宝/微信(有真实时分);银行 PDF 无时间默认 00:00,会把高峰误判到 0 点
    hr_src = con[con['来源'].isin(['支付宝', '微信'])] if '来源' in con.columns else con
    hr = hr_src.groupby(hr_src['交易时间'].dt.hour)['金额'].sum()
    by_day = con.groupby(con['交易时间'].dt.strftime('%Y-%m-%d'))['金额'].sum()
    busiest_day = by_day.idxmax() if len(by_day) else None
    data['profile'] = {
        'active_days': int(active_days),
        'avg_per_active_day': _r(real_expense / active_days) if active_days else 0,
        'avg_per_tx': _r(real_expense / len(con)),
        'peak_weekday': _WEEKDAY[int(wk.idxmax())] if len(wk) else None,
        'peak_hour': int(hr.idxmax()) if len(hr) else None,
        'busiest_day': busiest_day,
        'busiest_day_amount': _r(by_day.max()) if len(by_day) else 0,
        'top_merchant': None,
    }
    mer = con.groupby('交易对方')['金额'].agg(['sum', 'count'])
    mer = mer[mer.index.astype(str).str.len() > 1]
    if len(mer):
        tm = mer.sort_values('count', ascending=False).head(1)
        data['profile']['top_merchant'] = {'name': str(tm.index[0])[:24],
                                            'count': int(tm['count'].iloc[0]),
                                            'amount': _r(tm['sum'].iloc[0])}

    # 订阅 / 境外 / 异常 摘要(各自模块已按真实消费口径)
    try:
        from services import recurring
        rec = recurring.detect(df, year)
        data['subscriptions'] = {'count': rec['count'], 'monthly_total': rec['monthly_total'],
                                 'annual_total': rec['annual_total'], 'top': rec['items'][:5]}
    except Exception:
        logger.exception('年度报告:订阅摘要失败')
        data['subscriptions'] = None
    try:
        from services import overseas
        ov = overseas.detect(df, year)
        data['overseas'] = {'count': ov['count'], 'total_cny': ov['total_cny'],
                            'by_currency': ov['by_currency'][:5], 'by_region': ov.get('by_region', [])[:5]}
    except Exception:
        logger.exception('年度报告:境外摘要失败')
        data['overseas'] = None
    try:
        from services import anomaly
        an = anomaly.detect(df, limit=5)
        data['anomalies'] = {'count': an['count'], 'top': an['alerts'][:5]}
    except Exception:
        logger.exception('年度报告:异常摘要失败')
        data['anomalies'] = None

    # 净资产(最新快照,跨年也展示)
    try:
        from services import networth
        t = networth.trend(uid)
        if t:
            data['net_worth'] = {'date': t[-1]['date'], 'net': t[-1]['net'],
                                 'assets': t[-1]['assets'], 'liabilities': t[-1]['liabilities']}
    except Exception:
        data['net_worth'] = None

    return data


# ============ AI 文案 ============
def _report_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_annual_reports.json')


def _load(uid):
    try:
        p = _report_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save(uid, d):
    p = _report_file(uid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def get_cached_narrative(uid, year):
    return _load(uid).get(str(year))


def _compact(data):
    """给模型的精简版(去掉长列表细节,保留关键数字)。"""
    return {
        '年份': data.get('year'),
        '真实消费': data.get('real_expense'), '真实收入': data.get('real_income'),
        '结余': data.get('saving'), '储蓄率%': data.get('saving_rate'),
        '消费笔数': data.get('tx_count'),
        '消费最高月': data.get('peak_month'),
        'top分类': [{'分类': c['category'], '金额': c['amount']} for c in data.get('top_categories', [])[:8]],
        '最大单笔': data.get('biggest', [])[:3],
        '消费画像': {k: data['profile'].get(k) for k in
                 ('active_days', 'avg_per_active_day', 'peak_weekday', 'peak_hour', 'busiest_day', 'top_merchant')}
                 if data.get('profile') else {},
        '订阅定期扣费': (data.get('subscriptions') or {}).get('monthly_total') and {
            '笔数': data['subscriptions']['count'], '月成本': data['subscriptions']['monthly_total'],
            '年成本': data['subscriptions']['annual_total']} or None,
        '境外消费': (data.get('overseas') or {}).get('total_cny') and {
            '笔数': data['overseas']['count'], '人民币合计': data['overseas']['total_cny']} or None,
        '异常提醒数': (data.get('anomalies') or {}).get('count'),
        '净资产': data.get('net_worth'),
    }


def narrative(uid, df, year=None, force=False, cfg=None):
    """生成(或取缓存)年度账单 AI 小结。"""
    data = build_data(df, uid, year)
    if data.get('empty'):
        raise ValueError('该年度没有可用的消费数据')
    year = data['year']
    cache = _load(uid)
    if not force and str(year) in cache and cache[str(year)].get('summary'):
        r = dict(cache[str(year)])
        r['cached'] = True
        return r

    cfg = cfg or ai_svc.get_ai_config(uid, 'analysis')
    if not cfg.get('api_key'):
        raise RuntimeError('AI 未配置(请到设置→AI 与模型 指定「智能分析」用的模型)')
    system = (
        "你是一位懂生活也懂理财的年度账单主理人。下面是用户这一年的『年度账单数据』(金额单位元,均为真实口径)。"
        "请写一段有温度、像朋友复盘的中文『年度账单小结』,用 Markdown。要求:\n"
        "1. 绝不编造数据里没有的数字;\n"
        "2. 结构:**🎬 开场**(一句话总结这一年花钱的画像) → **💸 钱都去哪了**(最大头分类、消费最高的月份、最大单笔,讲出故事感) → "
        "**🔁 固定开销**(订阅/定期扣费的月成本年成本,提示有没有可以砍的) → **🌍 走出国门**(若有境外消费) → "
        "**💰 攒下了多少**(结余/储蓄率/净资产,客观但鼓励) → **🎯 明年小目标**(2-3 条务实建议);\n"
        "3. 关键数字加粗,语气温暖不说教,总篇幅 400 字内;没有的板块(如无境外)就跳过不提。"
    )
    user = f"年度账单数据:\n```json\n{json.dumps(_compact(data), ensure_ascii=False, indent=1)}\n```"
    resp = ai_svc._post_messages({
        'model': cfg.get('model') or '', 'max_tokens': 1500, 'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }, cfg=cfg, timeout=90)
    text = ''.join(c.get('text', '') for c in resp.get('content', []) if c.get('type') == 'text').strip()
    if not text:
        raise RuntimeError('模型未返回内容')
    record = {'year': year, 'summary': text,
              'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              'model': resp.get('model', cfg.get('model', ''))}
    cache[str(year)] = record
    _save(uid, cache)
    out = dict(record)
    out['cached'] = False
    return out
