"""
AI 智能分析:对某个分析维度(scope)的聚合数据生成中文 Markdown 洞察报告。

- 复用现有 DataFrame,按 scope 抽取紧凑的结构化统计 → 交给模型解读(不让模型碰原始流水,只给汇总数字,避免编造)。
- 结果缓存到 upload/<uid>/_ai_reports.json,按 scope+周期 复用;前端可「自动(每月)」或「手动」触发。
"""
import json
import logging
import os
from datetime import datetime

import pandas as pd

from config import UPLOAD_FOLDER
from services import ai as ai_svc

logger = logging.getLogger(__name__)

SCOPES = ('yearly', 'monthly', 'category', 'time', 'channel', 'reconcile', 'income')
SCOPE_LABELS = {
    'yearly': '年度总览', 'monthly': '月度分析', 'category': '分类分析',
    'time': '时间分析', 'channel': '渠道分析', 'reconcile': '对账中心', 'income': '收入分析',
}
MAX_REPORTS = 40


def _reports_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_ai_reports.json')


def _load_reports(uid):
    try:
        p = _reports_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save_reports(uid, reports):
    # 只保留最近 MAX_REPORTS 条
    if len(reports) > MAX_REPORTS:
        items = sorted(reports.items(), key=lambda kv: kv[1].get('generated_at', ''), reverse=True)
        reports = dict(items[:MAX_REPORTS])
    p = _reports_file(uid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return reports


def period_key(scope, year, month):
    if scope == 'monthly':
        return f"monthly:{year}-{int(month or 0):02d}"
    return f"{scope}:{year}"


def get_cached(uid, scope, year, month):
    return _load_reports(uid).get(period_key(scope, year, month))


# ============ 各维度的紧凑统计 ============
def _round(v, n=2):
    try:
        return round(float(v), n)
    except Exception:
        return 0.0


def _expense(df):
    d = df
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d[d['收/支'] == '支出']


def _top_cat(df, n=12):
    e = _expense(df)
    if e.empty:
        return []
    g = e.groupby('交易分类')['金额'].agg(['sum', 'count']).sort_values('sum', ascending=False).head(n)
    return [{'分类': str(k), '金额': _round(r['sum']), '笔数': int(r['count'])} for k, r in g.iterrows()]


def _totals(df):
    d = df
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    out = {}
    for t in ('收入', '支出', '转入', '转出'):
        out[t] = _round(d[d['收/支'] == t]['金额'].sum())
    out['结余'] = _round(out['收入'] - out['支出'])
    out['支出笔数'] = int((d['收/支'] == '支出').sum())
    return out


def build_summary(df, scope, year, month):
    """构造交给模型的紧凑统计。返回 (year, month, period_label, payload_dict)。"""
    df = df.copy()
    years = sorted(df['交易时间'].dt.year.unique().tolist())
    if not year:
        year = years[-1] if years else datetime.now().year
    year = int(year)
    month = int(month) if month else None
    ydf = df[df['交易时间'].dt.year == year]

    if scope == 'yearly':
        last = df[df['交易时间'].dt.year == year - 1]
        monthly = ydf[ydf['收/支'] == '支出']
        if '是否退款' in monthly.columns:
            monthly = monthly[~monthly['是否退款'].fillna(False)]
        mtrend = monthly.groupby(monthly['交易时间'].dt.month)['金额'].sum()
        members = []
        if '成员' in ydf.columns:
            mg = _expense(ydf).groupby('成员')['金额'].sum().sort_values(ascending=False)
            members = [{'成员': str(k), '支出': _round(v)} for k, v in mg.items()]
        natures = {}
        if '资金性质' in ydf.columns:
            ng = ydf.groupby('资金性质')['金额'].sum().sort_values(ascending=False)
            natures = {str(k): _round(v) for k, v in ng.items()}
        return year, None, f"{year} 年度", {
            '本年汇总': _totals(ydf), '上一年支出': _totals(last).get('支出'),
            '逐月支出': {str(int(m)): _round(v) for m, v in mtrend.items()},
            'top分类': _top_cat(ydf), '成员支出': members,
            '资金性质构成(消费=真实消费,工资/投资/其他收入=真实收入,其余为非收支流动)': natures,
        }

    if scope == 'monthly':
        month = month or (int(ydf['交易时间'].dt.month.max()) if len(ydf) else datetime.now().month)
        mdf = ydf[ydf['交易时间'].dt.month == month]
        lm_year, lm_month = (year, month - 1) if month > 1 else (year - 1, 12)
        lmdf = df[(df['交易时间'].dt.year == lm_year) & (df['交易时间'].dt.month == lm_month)]
        e = _expense(mdf)
        daily = e.groupby(e['交易时间'].dt.day)['金额'].sum()
        big = e.sort_values('金额', ascending=False).head(8)
        return year, month, f"{year}-{month:02d}", {
            '本月汇总': _totals(mdf), '上月支出': _totals(lmdf).get('支出'),
            '逐日支出': {str(int(d)): _round(v) for d, v in daily.items()},
            'top分类': _top_cat(mdf),
            '最大支出': [{'日期': r['交易时间'].strftime('%m-%d'), '金额': _round(r['金额']),
                       '分类': str(r['交易分类']), '说明': str(r.get('商品说明', ''))[:24]}
                      for _, r in big.iterrows()],
        }

    if scope == 'category':
        e = _expense(ydf)
        g = e.groupby('交易分类')['金额'].agg(['sum', 'count', 'mean']).sort_values('sum', ascending=False).head(15)
        total = _round(e['金额'].sum())
        rows = [{'分类': str(k), '金额': _round(r['sum']), '笔数': int(r['count']),
                 '客单价': _round(r['mean']), '占比%': _round(r['sum'] / total * 100 if total else 0, 1)}
                for k, r in g.iterrows()]
        return year, None, f"{year} 年", {'年支出合计': total, '分类明细': rows}

    if scope == 'time':
        e = _expense(ydf)
        hourly = e.groupby(e['交易时间'].dt.hour)['金额'].sum()
        wk = e[~e['交易时间'].dt.dayofweek.isin([5, 6])]['金额'].sum()
        we = e[e['交易时间'].dt.dayofweek.isin([5, 6])]['金额'].sum()
        night = e[e['交易时间'].dt.hour.isin([0, 1, 2, 3, 4, 23])]['金额'].sum()
        return year, None, f"{year} 年", {
            '各时段支出': {str(int(h)): _round(v) for h, v in hourly.items()},
            '工作日支出': _round(wk), '周末支出': _round(we), '深夜(23-4点)支出': _round(night),
            'top分类': _top_cat(ydf, 8),
        }

    if scope == 'income':
        try:
            from services import income as income_svc
            rep = income_svc.full_report(df, year)
            sal = rep['salary']
            return year, None, f"{year} 年", {
                '收入总览': rep['overview'],
                '薪资统计': sal.get('stats', {}),
                '近12个月发薪明细(amount=实发,is_bonus=奖金月,saving_rate=工资结余率%)':
                    sal.get('months', [])[-12:],
                '薪资口径审计(off_channel=非工资卡的工资行,missed=工资卡大额入账未标工资)': sal.get('audit', {}),
                '理财收益': {k: v for k, v in rep['invest'].items() if k != 'months'},
                '其他收入分组': rep['other'].get('groups', []),
            }
        except Exception as e:
            logger.warning(f"income summary fallback: {e}")
            return year, None, f"{year} 年", {'汇总': _totals(ydf)}

    if scope == 'reconcile':
        try:
            from services import reconcile as rec_svc
            wf = rec_svc.waterfall(df, year)
            fd = rec_svc.feeds(df, year)
            cr = rec_svc.credit(df, year)
            sus = rec_svc.suspects(df, year)
            feeds_brief = [{'平台': p['platform'], '平台侧卡出资': p['platform_card_out_total'],
                            '银行侧喂养': p['bank_feed_total']} for p in fd.get('platforms', [])]
            return year, None, f"{year} 年", {
                '流出口径(从总流出剥离到真实消费)': wf['outflow'],
                '流入口径(从总流入剥离到真实收入)': wf['inflow'],
                '真实消费': wf['real_expense'], '真实收入': wf['real_income'],
                '内部搬运(不计收支)': wf['neutral'],
                '平台喂养对账(两侧量级应接近)': feeds_brief,
                '信用卡消费vs还款': {'消费合计': cr.get('consume_total'), '还款合计': cr.get('repay_total')},
                '疑似双算组数': len(sus),
                '疑似双算样例(不同来源同日同金额)': sus[:5],
            }
        except Exception as e:
            logger.warning(f"reconcile summary fallback: {e}")
            return year, None, f"{year} 年", {'汇总': _totals(ydf)}

    if scope == 'channel':
        try:
            from services.analysis import analyze_channels
            ch = analyze_channels(ydf)
            chans = ch.get('channels', []) if isinstance(ch, dict) else []
            rows = [{'渠道': c.get('label'), '支出': _round(c.get('expense', 0)),
                     '笔数': int(c.get('count', 0) or 0), '占比%': _round(c.get('expense_ratio', 0), 1)}
                    for c in chans[:12]]
            return year, None, f"{year} 年", {'渠道明细': rows, '年支出合计': _totals(ydf).get('支出')}
        except Exception as e:
            logger.warning(f"channel summary fallback: {e}")
            return year, None, f"{year} 年", {'年支出合计': _totals(ydf).get('支出'), 'top分类': _top_cat(ydf)}

    return year, None, f"{year} 年", {'汇总': _totals(ydf), 'top分类': _top_cat(ydf)}


def _build_prompt(scope, period_label, payload):
    label = SCOPE_LABELS.get(scope, scope)
    data_json = json.dumps(payload, ensure_ascii=False, indent=1)
    if scope == 'income':
        system = (
            "你是个人收入与职业财务顾问。下面是用户的『收入分析数据』:薪资逐月明细(已识别奖金月)、"
            "薪资统计(平均/中位/发薪日/同比/储蓄率)、口径审计、理财收益与其他收入。"
            "请写一份简明的中文收入分析报告,用 Markdown。要求:\n"
            "1. 不要编造数字;\n"
            "2. 结构:**💼 薪资画像**(月薪水平、稳定性、奖金规律、同比变化) → "
            "**💰 储蓄能力**(工资结余率,消费是否吃掉工资,被动收入/其他收入的补充作用) → "
            "**🔍 口径提示**(若审计列表非空,提醒核对) → **💡 建议**(2-3 条:储蓄/收入结构优化,务实);\n"
            "3. 关键数字加粗;总篇幅控制在 350 字内。"
        )
    elif scope == 'reconcile':
        system = (
            "你是个人财务审计师。下面是用户账单的『口径对账数据』:多渠道账单(支付宝/微信/银行卡/信用卡)"
            "合并后,按资金性质把总流水剥离成 真实消费/真实收入/内部流转/还款/投资/往来。"
            "请写一份简明的中文审计报告,用 Markdown。要求:\n"
            "1. 不要编造数字;\n"
            "2. 结构:**🧾 口径结论**(真实消费/真实收入是多少,占总流水的比例,说明大头都被剥离到了哪些非消费桶) → "
            "**🔍 健康度检查**(平台喂养两侧量级是否接近、信用卡消费与还款是否匹配、疑似双算是否值得人工核对) → "
            "**⚠️ 风险提示**(哪里口径可能不准、建议导入什么数据或加什么规则);\n"
            "3. 关键数字加粗;总篇幅控制在 350 字内,结论要可执行。"
        )
    else:
        system = (
            "你是资深个人理财分析师。下面给你一份用户账单的『结构化统计数据』(已聚合,金额单位元)。"
            "请基于这些数字写一份简明的中文分析报告,用 Markdown。要求:\n"
            "1. 不要编造数据里没有的数字,也不要罗列原始 JSON;\n"
            "2. 结构:**📊 概览** → **🔍 亮点与异常**(指出最大头支出/明显波动/集中度) → **📈 趋势解读**(同比/环比/分布) → **💡 建议**(2-3 条可执行的优化/省钱建议);\n"
            "3. 关键数字加粗,适当用列表;总篇幅控制在 350 字内,务实不空话。"
        )
    user = f"分析维度:{label}({period_label})\n\n结构化统计数据:\n```json\n{data_json}\n```"
    return system, user


def generate(uid, df, scope, year=None, month=None, force=False, cfg=None):
    """生成(或取缓存)某维度的 AI 分析报告。返回 {scope, period, period_label, summary, generated_at, model, cached}。"""
    if scope not in SCOPES:
        raise ValueError('未知分析维度')
    real_year, real_month, period_label, payload = build_summary(df, scope, year, month)
    key = period_key(scope, real_year, real_month)
    reports = _load_reports(uid)
    if not force and key in reports and reports[key].get('summary'):
        r = dict(reports[key])
        r['cached'] = True
        return r

    cfg = cfg or ai_svc.get_ai_config(uid, 'analysis')
    if not cfg.get('api_key'):
        raise RuntimeError('AI 未配置(请到设置→AI 与模型 指定「智能分析」用的模型)')
    system, user = _build_prompt(scope, period_label, payload)
    resp = ai_svc._post_messages({
        'model': cfg.get('model') or '', 'max_tokens': 1200, 'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }, cfg=cfg, timeout=90)
    text = ''.join(c.get('text', '') for c in resp.get('content', []) if c.get('type') == 'text').strip()
    if not text:
        raise RuntimeError('模型未返回内容')

    record = {
        'scope': scope, 'period': key, 'period_label': period_label,
        'summary': text, 'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model': resp.get('model', cfg.get('model', '')),
    }
    reports[key] = record
    _save_reports(uid, reports)
    out = dict(record)
    out['cached'] = False
    return out
