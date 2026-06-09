"""
AI 服务:调用 Anthropic 兼容端点(默认 Kimi)。

两个能力:
1. chat_over_transactions —— 对话式智能检索/分析当前用户的交易(工具调用循环,模型自己决定怎么查 DataFrame)。
2. recognize_bill —— 智能识别未知格式账单文本 → 归一为本系统 schema 的交易数组(供预览/导入)。
"""
import json
import logging
import re

import pandas as pd
import requests

from config import AI_BASE_URL, AI_API_KEY, AI_MODEL

logger = logging.getLogger(__name__)

VALID_TYPES = ['收入', '支出', '转入', '转出', '不计收支']


def _post_messages(payload, timeout=120):
    url = AI_BASE_URL + '/v1/messages'
    headers = {
        'x-api-key': AI_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if r.status_code >= 400:
        logger.error(f"AI 端点错误 {r.status_code}: {r.text[:400]}")
        r.raise_for_status()
    return r.json()


# ============ 1. 对话式检索交易 ============
_QUERY_TOOL = {
    'name': 'query_transactions',
    'description': '按条件查询/聚合当前用户的交易记录。返回笔数、金额合计、可选分组合计、以及样本明细。用它回答任何关于消费/收入/转账的问题。',
    'input_schema': {
        'type': 'object',
        'properties': {
            'start_date': {'type': 'string', 'description': '起始日期 YYYY-MM-DD(含)'},
            'end_date': {'type': 'string', 'description': '结束日期 YYYY-MM-DD(含)'},
            'type': {'type': 'string', 'enum': VALID_TYPES, 'description': '收/支类型'},
            'category': {'type': 'string', 'description': '交易分类(子串匹配,如 餐饮/交通/购物)'},
            'keyword': {'type': 'string', 'description': '关键字(匹配商品说明/交易对方/分类)'},
            'member': {'type': 'string', 'description': '成员名(如 本人/老婆)'},
            'source': {'type': 'string', 'description': '来源:支付宝/微信/银行'},
            'min_amount': {'type': 'number'},
            'max_amount': {'type': 'number'},
            'group_by': {'type': 'string', 'enum': ['category', 'month', 'member', 'source', 'counterparty'],
                         'description': '分组维度,返回各组金额合计'},
            'limit': {'type': 'integer', 'description': '返回明细样本条数,默认10,最多30'},
        },
    },
}

_OVERVIEW_TOOL = {
    'name': 'data_overview',
    'description': '获取数据概览:时间范围、总笔数、各成员/来源/分类清单、收支/转账合计。先调它了解数据全貌。',
    'input_schema': {'type': 'object', 'properties': {}},
}


def _run_query(df, args):
    d = df.copy()
    info = {}
    if args.get('start_date'):
        d = d[d['交易时间'] >= pd.to_datetime(args['start_date'])]
    if args.get('end_date'):
        d = d[d['交易时间'] < pd.to_datetime(args['end_date']) + pd.Timedelta(days=1)]
    if args.get('type') in VALID_TYPES:
        d = d[d['收/支'] == args['type']]
    if args.get('category'):
        d = d[d['交易分类'].astype(str).str.contains(args['category'], case=False, na=False)]
    if args.get('member') and '成员' in d.columns:
        d = d[d['成员'].astype(str).str.contains(args['member'], case=False, na=False)]
    if args.get('source') and '来源' in d.columns:
        d = d[d['来源'].astype(str).str.contains(args['source'], case=False, na=False)]
    if args.get('keyword'):
        kw = args['keyword']
        d = d[d['商品说明'].astype(str).str.contains(kw, case=False, na=False) |
              d['交易对方'].astype(str).str.contains(kw, case=False, na=False) |
              d['交易分类'].astype(str).str.contains(kw, case=False, na=False)]
    if args.get('min_amount') is not None:
        d = d[d['金额'] >= float(args['min_amount'])]
    if args.get('max_amount') is not None:
        d = d[d['金额'] <= float(args['max_amount'])]
    if '是否退款' in d.columns:
        d = d[~d['是否退款']]

    info['count'] = int(len(d))
    info['total_amount'] = round(float(d['金额'].sum()), 2)

    gb = args.get('group_by')
    colmap = {'category': '交易分类', 'member': '成员', 'source': '来源', 'counterparty': '交易对方'}
    if gb == 'month':
        g = d.groupby(d['交易时间'].dt.strftime('%Y-%m'))['金额'].agg(['sum', 'count'])
        info['groups'] = [{'key': k, 'amount': round(float(r['sum']), 2), 'count': int(r['count'])}
                          for k, r in g.iterrows()]
    elif gb in colmap and colmap[gb] in d.columns:
        g = d.groupby(colmap[gb])['金额'].agg(['sum', 'count']).sort_values('sum', ascending=False).head(20)
        info['groups'] = [{'key': str(k), 'amount': round(float(r['sum']), 2), 'count': int(r['count'])}
                          for k, r in g.iterrows()]

    limit = min(int(args.get('limit', 10) or 10), 30)
    sample = d.sort_values('交易时间', ascending=False).head(limit)
    info['sample'] = [{
        'time': r['交易时间'].strftime('%Y-%m-%d %H:%M'),
        'type': str(r['收/支']), 'category': str(r['交易分类']),
        'counterparty': str(r.get('交易对方', '')), 'desc': str(r.get('商品说明', ''))[:40],
        'amount': round(float(r['金额']), 2),
        'member': str(r.get('成员', '')), 'source': str(r.get('来源', '')),
    } for _, r in sample.iterrows()]
    return info


def _run_overview(df):
    d = df
    out = {'count': int(len(d))}
    if len(d):
        out['date_range'] = [d['交易时间'].min().strftime('%Y-%m-%d'), d['交易时间'].max().strftime('%Y-%m-%d')]
        for col, key in [('成员', 'members'), ('来源', 'sources')]:
            if col in d.columns:
                out[key] = sorted(d[col].dropna().astype(str).unique().tolist())
        out['categories'] = d['交易分类'].dropna().astype(str).value_counts().head(25).index.tolist()
        by = d.groupby('收/支')['金额'].sum()
        out['by_type'] = {str(k): round(float(v), 2) for k, v in by.items()}
    return out


def chat_over_transactions(df, question, history=None):
    """对话式检索。history: [{'role','content'}]。返回 {answer, tool_calls}。"""
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    system = (
        f"你是个人账单分析助手。今天是 {today}。用户的全部交易通过工具查询,你不能编造数字——"
        f"任何涉及金额/笔数/明细的回答都必须先调用工具拿到真实数据再回答。\n"
        f"字段说明:『收/支』取值 收入/支出/转入/转出/不计收支(转入转出=转账,不计收支=内部搬运/理财申赎,真实花费只看『支出』)。"
        f"金额单位元。回答用中文,简洁,给出关键数字和必要的对比/明细,不要罗列原始 JSON。"
    )
    messages = []
    for h in (history or [])[-6:]:
        if h.get('role') in ('user', 'assistant') and h.get('content'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': question})

    tool_calls = []
    for _ in range(6):
        resp = _post_messages({
            'model': AI_MODEL, 'max_tokens': 1500, 'system': system,
            'messages': messages, 'tools': [_QUERY_TOOL, _OVERVIEW_TOOL],
        })
        content = resp.get('content', [])
        messages.append({'role': 'assistant', 'content': content})
        tool_uses = [c for c in content if c.get('type') == 'tool_use']
        if not tool_uses:
            text = ''.join(c.get('text', '') for c in content if c.get('type') == 'text')
            return {'answer': text.strip() or '（无回复）', 'tool_calls': tool_calls}
        results = []
        for tu in tool_uses:
            name, args = tu.get('name'), tu.get('input', {}) or {}
            try:
                out = _run_overview(df) if name == 'data_overview' else _run_query(df, args)
            except Exception as e:
                out = {'error': str(e)}
            tool_calls.append({'name': name, 'input': args,
                               'count': out.get('count'), 'total': out.get('total_amount')})
            results.append({'type': 'tool_result', 'tool_use_id': tu.get('id'),
                            'content': json.dumps(out, ensure_ascii=False)})
        messages.append({'role': 'user', 'content': results})
    return {'answer': '查询轮次过多,请把问题问得更具体一些。', 'tool_calls': tool_calls}


# ============ 2. 智能识别账单 ============
def _extract_json_array(text):
    m = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.S)
    raw = m.group(1) if m else None
    if raw is None:
        s, e = text.find('['), text.rfind(']')
        raw = text[s:e + 1] if s != -1 and e != -1 and e > s else None
    if raw is None:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def recognize_bill(text_content, hint=''):
    """把任意原始账单文本解析为本系统 schema 的交易数组(供预览)。返回 list[dict]。"""
    text_content = (text_content or '')[:18000]
    system = (
        "你是账单解析器。把用户提供的原始账单文本解析为 JSON 数组,每个元素字段固定为:"
        '"交易时间"(YYYY-MM-DD HH:MM:SS,缺时分秒补 00:00:00)、"交易分类"、"交易对方"、'
        '"商品说明"、"收支"(只能是 收入/支出/转入/转出/不计收支)、"金额"(正数字符串)、"收付款方式"。'
        "判定收支:消费/付款=支出,收款/工资=收入,转给别人或自己=转出/转入。"
        "只输出 JSON 数组,不要任何解释或 markdown 之外的文字。无法确定的字段填空字符串。"
    )
    prompt = (f"账单来源提示:{hint}\n\n原始内容:\n{text_content}" if hint else f"原始内容:\n{text_content}")
    resp = _post_messages({
        'model': AI_MODEL, 'max_tokens': 4000, 'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    })
    text = ''.join(c.get('text', '') for c in resp.get('content', []) if c.get('type') == 'text')
    rows = _extract_json_array(text)
    norm = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        zhi = str(r.get('收支') or r.get('收/支') or '').strip()
        if zhi not in VALID_TYPES:
            zhi = '支出'
        try:
            amt = abs(float(str(r.get('金额', '0')).replace(',', '').replace('¥', '').strip() or 0))
        except Exception:
            amt = 0.0
        norm.append({
            '交易时间': str(r.get('交易时间', '')).strip(),
            '交易分类': str(r.get('交易分类', '')).strip(),
            '交易对方': str(r.get('交易对方', '')).strip(),
            '商品说明': str(r.get('商品说明', '')).strip(),
            '收/支': zhi,
            '金额': round(amt, 2),
            '收/付款方式': str(r.get('收付款方式') or r.get('收/付款方式') or '').strip(),
        })
    return norm
