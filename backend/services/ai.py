"""
AI 服务:调用 Anthropic 兼容端点(默认 Kimi)。

两个能力:
1. chat_over_transactions —— 对话式智能检索/分析当前用户的交易(工具调用循环,模型自己决定怎么查 DataFrame)。
2. recognize_bill —— 智能识别未知格式账单文本 → 归一为本系统 schema 的交易数组(供预览/导入)。
"""
import json
import logging
import os
import re
import secrets
import threading

import pandas as pd
import requests

from config import AI_BASE_URL, AI_API_KEY, AI_MODEL, AI_ENABLED, UPLOAD_FOLDER

AI_ENABLED_ENV = bool(AI_ENABLED)

logger = logging.getLogger(__name__)
_cfg_lock = threading.RLock()

VALID_TYPES = ['收入', '支出', '转入', '转出', '不计收支']

# 可按功能分别指定模型的「用途」(不是每个模型都有多模态识别能力,故分开)
PURPOSES = ('chat', 'recognize', 'analysis')
PURPOSE_LABELS = {'chat': '对话助手', 'recognize': '账单识别', 'analysis': '智能分析'}
MAX_PROFILES = 12


# ============ 每用户模型配置 ============
# 存 upload/<uid>/_ai_config.json。新结构:
#   {
#     "profiles": [{"id","name","base_url","api_key","model"}],   # 多套模型配置档案
#     "assignments": {"chat": "<pid|''>", "recognize": "...", "analysis": "..."},  # 功能→档案
#     "default_profile": "<pid|''>",   # 未单独指定时用的默认档案
#     "custom_providers": [{"name","base_url","model"}],   # 自定义供应商模板(无 key)
#     "auto_analyze": true             # AI 智能分析每月自动触发
#   }
# 兼容旧结构(顶层 base_url/api_key/model)→自动迁移成一个名为「默认配置」的档案。
def _cfg_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_ai_config.json')


def _load_user_cfg(uid):
    try:
        p = _cfg_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _new_pid():
    return 'p' + secrets.token_hex(4)


def _norm_profile(p, allow_new_id=True):
    """规范化单个档案;返回 dict 或 None。"""
    if not isinstance(p, dict):
        return None
    pid = str(p.get('id') or '').strip()[:40]
    if not pid and allow_new_id:
        pid = _new_pid()
    if not pid:
        return None
    return {
        'id': pid,
        'name': (str(p.get('name', '')).strip() or '未命名')[:24],
        'base_url': str(p.get('base_url', '')).strip()[:200],
        'api_key': str(p.get('api_key', '') or ''),
        'model': str(p.get('model', '')).strip()[:80],
    }


def _normalized(uid):
    """读取并规范化用户配置(含迁移)。返回完整结构(profiles 含明文 key,仅服务端内部用)。"""
    raw = _load_user_cfg(uid)
    if not isinstance(raw, dict):
        raw = {}
    profiles_raw = raw.get('profiles')
    if not isinstance(profiles_raw, list):
        profiles_raw = []
        # 迁移旧版单配置
        if raw.get('api_key') or raw.get('base_url') or raw.get('model'):
            profiles_raw = [{
                'id': 'default', 'name': '默认配置',
                'base_url': raw.get('base_url', ''),
                'api_key': raw.get('api_key', ''),
                'model': raw.get('model', ''),
            }]
    profiles = []
    seen = set()
    for p in profiles_raw[:MAX_PROFILES]:
        np = _norm_profile(p)
        if np and np['id'] not in seen:
            seen.add(np['id'])
            profiles.append(np)

    pids = {p['id'] for p in profiles}
    assignments_raw = raw.get('assignments') if isinstance(raw.get('assignments'), dict) else {}
    assignments = {}
    for k in PURPOSES:
        v = str(assignments_raw.get(k, '') or '').strip()
        assignments[k] = v if v in pids else ''

    default_profile = str(raw.get('default_profile', '') or '').strip()
    if default_profile not in pids:
        default_profile = profiles[0]['id'] if profiles else ''

    cps = []
    for cp in (raw.get('custom_providers') or [])[:20]:
        if not isinstance(cp, dict):
            continue
        name = str(cp.get('name', '')).strip()[:20]
        burl = str(cp.get('base_url', '')).strip()
        if name and burl.startswith(('http://', 'https://')):
            cps.append({'name': name, 'base_url': burl, 'model': str(cp.get('model', '')).strip()[:80]})

    return {
        'profiles': profiles,
        'assignments': assignments,
        'default_profile': default_profile,
        'custom_providers': cps,
        'auto_analyze': bool(raw.get('auto_analyze', True)),
    }


def _save_normalized(uid, cfg):
    p = _cfg_file(uid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    try:
        os.chmod(p, 0o600)   # 含 key,仅属主可读
    except Exception:
        pass


def get_ai_config(uid, purpose='chat'):
    """返回该用户某功能(purpose)生效的 AI 配置 {base_url, api_key, model, source, ...}。
    功能分配优先 → 默认档案 → 环境变量默认(若部署方配置了)。"""
    cfg = _normalized(uid)
    profiles = cfg['profiles']
    pid = cfg['assignments'].get(purpose, '') or cfg['default_profile']
    prof = next((p for p in profiles if p['id'] == pid), None)
    if prof is None and profiles:
        prof = profiles[0]
    if prof and prof.get('api_key'):
        return {
            'base_url': (prof['base_url'] or AI_BASE_URL).rstrip('/'),
            'api_key': prof['api_key'],
            'model': prof['model'] or AI_MODEL,
            'source': 'custom',
            'profile_id': prof['id'],
            'profile_name': prof['name'],
            'custom_providers': cfg['custom_providers'],
        }
    return {'base_url': AI_BASE_URL, 'api_key': AI_API_KEY, 'model': AI_MODEL,
            'source': 'default', 'profile_id': None, 'profile_name': None,
            'custom_providers': cfg['custom_providers']}


def public_config(uid):
    """对前端可见的配置:key 一律掩码,绝不下发明文。"""
    cfg = _normalized(uid)
    profiles = [{
        'id': p['id'], 'name': p['name'], 'base_url': p['base_url'], 'model': p['model'],
        'has_key': bool(p['api_key']), 'api_key_masked': mask_key(p['api_key']),
    } for p in cfg['profiles']]
    return {
        'profiles': profiles,
        'assignments': cfg['assignments'],
        'default_profile': cfg['default_profile'],
        'custom_providers': cfg['custom_providers'],
        'auto_analyze': cfg['auto_analyze'],
        'purposes': [{'key': k, 'label': PURPOSE_LABELS[k]} for k in PURPOSES],
        'has_default': AI_ENABLED_ENV,
    }


def upsert_profile(uid, profile):
    """新增或更新一个档案。profile: {id?, name, base_url, model, api_key?}。
    api_key: 缺省/None=保留旧值 / ''=清除 / 其他=替换。返回完整(明文)结构。"""
    with _cfg_lock:
        cfg = _normalized(uid)
        pid = str((profile or {}).get('id') or '').strip()
        incoming_key = profile.get('api_key', None) if isinstance(profile, dict) else None
        existing = next((p for p in cfg['profiles'] if p['id'] == pid), None) if pid else None
        if existing:
            existing['name'] = (str(profile.get('name', existing['name'])).strip() or existing['name'])[:24]
            existing['base_url'] = str(profile.get('base_url', existing['base_url'])).strip()[:200]
            existing['model'] = str(profile.get('model', existing['model'])).strip()[:80]
            if incoming_key is not None:
                existing['api_key'] = '' if incoming_key == '' else str(incoming_key)
            saved = existing
        else:
            if len(cfg['profiles']) >= MAX_PROFILES:
                raise ValueError(f'模型配置档案最多 {MAX_PROFILES} 套')
            np = _norm_profile({
                'name': profile.get('name', ''), 'base_url': profile.get('base_url', ''),
                'model': profile.get('model', ''), 'api_key': incoming_key or '',
            })
            cfg['profiles'].append(np)
            saved = np
            if not cfg['default_profile']:
                cfg['default_profile'] = np['id']
        _save_normalized(uid, cfg)
        return saved['id'], public_config(uid)


def delete_profile(uid, pid):
    with _cfg_lock:
        cfg = _normalized(uid)
        cfg['profiles'] = [p for p in cfg['profiles'] if p['id'] != pid]
        pids = {p['id'] for p in cfg['profiles']}
        if cfg['default_profile'] == pid:
            cfg['default_profile'] = cfg['profiles'][0]['id'] if cfg['profiles'] else ''
        for k in PURPOSES:
            if cfg['assignments'].get(k) == pid:
                cfg['assignments'][k] = ''
        _save_normalized(uid, cfg)
        return public_config(uid)


def save_routing(uid, assignments=None, default_profile=None, custom_providers=None, auto_analyze=None):
    """保存功能分配/默认档案/自定义供应商模板/自动分析开关(不动档案与 key)。"""
    with _cfg_lock:
        cfg = _normalized(uid)
        pids = {p['id'] for p in cfg['profiles']}
        if isinstance(assignments, dict):
            for k in PURPOSES:
                if k in assignments:
                    v = str(assignments.get(k, '') or '').strip()
                    cfg['assignments'][k] = v if v in pids else ''
        if default_profile is not None:
            dp = str(default_profile or '').strip()
            cfg['default_profile'] = dp if dp in pids else (cfg['profiles'][0]['id'] if cfg['profiles'] else '')
        if custom_providers is not None and isinstance(custom_providers, list):
            cps = []
            for cp in custom_providers[:20]:
                if not isinstance(cp, dict):
                    continue
                name = str(cp.get('name', '')).strip()[:20]
                burl = str(cp.get('base_url', '')).strip()
                if name and burl.startswith(('http://', 'https://')):
                    cps.append({'name': name, 'base_url': burl, 'model': str(cp.get('model', '')).strip()[:80]})
            cfg['custom_providers'] = cps
        if auto_analyze is not None:
            cfg['auto_analyze'] = bool(auto_analyze)
        _save_normalized(uid, cfg)
        return public_config(uid)


def get_auto_analyze(uid):
    return _normalized(uid)['auto_analyze']


def mask_key(k):
    if not k:
        return ''
    return k[:7] + '…' + k[-4:] if len(k) > 14 else k[:3] + '…'


def test_ai_config(cfg):
    """对给定配置发一次最小请求,返回 (ok, message)。"""
    try:
        resp = _post_messages({'model': cfg['model'], 'max_tokens': 16,
                               'messages': [{'role': 'user', 'content': 'ping,只回复ok'}]},
                              cfg=cfg, timeout=30)
        txt = ''.join(c.get('text', '') for c in resp.get('content', []) if c.get('type') == 'text')
        return True, f"连接成功(模型 {resp.get('model', cfg['model'])} 回复: {txt[:40]})"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else '?'
        hint = {401: 'API Key 无效', 403: '无权限', 404: '端点路径不对(需 Anthropic 兼容 /v1/messages)'}.get(code, '')
        return False, f"HTTP {code} {hint}".strip()
    except Exception as e:
        return False, f"连接失败: {e}"


def _post_messages(payload, cfg=None, timeout=120):
    base = (cfg or {}).get('base_url') or AI_BASE_URL
    key = (cfg or {}).get('api_key') or AI_API_KEY
    url = base.rstrip('/') + '/v1/messages'
    headers = {
        'x-api-key': key,
        'authorization': f'Bearer {key}',   # 兼容只认 Bearer 的网关
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
            'nature': {'type': 'string',
                       'enum': ['消费', '工资收入', '投资收益', '其他收入', '退款', '报销',
                                '信用卡还款', '投资申赎', '内部流转', '转账往来', '其他'],
                       'description': '资金性质(经济本质):真实消费=消费;真实收入=工资收入/投资收益/其他收入;'
                                      '还款/投资/内部流转/转账往来都不算收支'},
            'min_amount': {'type': 'number'},
            'max_amount': {'type': 'number'},
            'group_by': {'type': 'string', 'enum': ['category', 'month', 'member', 'source', 'counterparty', 'nature'],
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

_EXPORT_TOOL = {
    'name': 'export_transactions',
    'description': '把符合条件的交易导出为可下载的文件(xlsx/csv)。用户要"导出/下载/给我文件/生成表格文件"时调用。返回下载 url,你必须在回答中用 Markdown 链接给出。',
    'input_schema': {
        'type': 'object',
        'properties': {
            **{k: v for k, v in _QUERY_TOOL['input_schema']['properties'].items()
               if k not in ('group_by', 'limit')},
            'format': {'type': 'string', 'enum': ['xlsx', 'csv'], 'description': '文件格式,默认 xlsx'},
            'name': {'type': 'string', 'description': '文件名(中文可,不带扩展名),如 6月支出明细'},
        },
    },
}

_EXPORT_COLS = ['交易时间', '交易分类', '交易对方', '商品说明', '收/支', '金额', '收/付款方式', '来源', '成员']
MAX_EXPORT_ROWS = 20000
MAX_EXPORT_FILES = 20


def _run_export(df, args, uid):
    """筛选→写文件到 upload/<uid>/_exports/,返回下载信息。"""
    import re as _re
    from datetime import datetime as _dt
    d = _apply_filters(df, args).sort_values('交易时间', ascending=False)
    if d.empty:
        return {'ok': False, 'error': '没有匹配的交易,无文件生成'}
    truncated = len(d) > MAX_EXPORT_ROWS
    d = d.head(MAX_EXPORT_ROWS)

    fmt = args.get('format') if args.get('format') in ('xlsx', 'csv') else 'xlsx'
    raw = (args.get('name') or '').strip() or f"账单导出_{_dt.now():%m%d}"
    safe = _re.sub(r'[^\w一-龥()-]', '', raw)[:30] or 'export'
    filename = f"{safe}_{_dt.now():%H%M%S}.{fmt}"

    exp_dir = os.path.join(UPLOAD_FOLDER, uid, '_exports')
    os.makedirs(exp_dir, exist_ok=True)
    path = os.path.join(exp_dir, filename)

    out = d[[c for c in _EXPORT_COLS if c in d.columns]].copy()
    out['交易时间'] = out['交易时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
    if fmt == 'xlsx':
        out.to_excel(path, index=False)
    else:
        out.to_csv(path, index=False, encoding='utf-8-sig')

    # 只保留最近 N 个导出文件
    try:
        files = sorted((os.path.join(exp_dir, f) for f in os.listdir(exp_dir)),
                       key=os.path.getmtime, reverse=True)
        for old in files[MAX_EXPORT_FILES:]:
            os.remove(old)
    except Exception:
        pass

    total = round(float(d['金额'].sum()), 2)
    return {'ok': True, 'filename': filename, 'url': f'/api/ai/exports/{filename}',
            'count': int(len(d)), 'total_amount': total, 'truncated': truncated,
            'hint': '请在回答中用 Markdown 链接提供下载,如 [📥 下载 ' + filename + '](url)'}


def _apply_filters(df, args):
    """query/export 共用的筛选逻辑。"""
    d = df.copy()
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
    if args.get('nature') and '资金性质' in d.columns:
        d = d[d['资金性质'] == args['nature']]
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
    return d


def _run_query(df, args):
    d = _apply_filters(df, args)
    info = {}
    info['count'] = int(len(d))
    info['total_amount'] = round(float(d['金额'].sum()), 2)

    gb = args.get('group_by')
    colmap = {'category': '交易分类', 'member': '成员', 'source': '来源',
              'counterparty': '交易对方', 'nature': '资金性质'}
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


def chat_over_transactions(df, question, history=None, cfg=None, uid=None):
    """对话式检索。history: [{'role','content'}]。返回 {answer, tool_calls}。"""
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    system = (
        f"你是个人账单分析助手。今天是 {today}。用户的全部交易通过工具查询,你不能编造数字——"
        f"任何涉及金额/笔数/明细的回答都必须先调用工具拿到真实数据再回答。\n"
        f"字段说明:『收/支』取值 收入/支出/转入/转出/不计收支(转入转出=转账,不计收支=内部搬运/理财申赎)。"
        f"『资金性质』(nature)是更准的经济口径:真实消费=消费;真实收入=工资收入/投资收益/其他收入;"
        f"信用卡还款/投资申赎/内部流转/转账往来 都不是真实收支。"
        f"用户问\"真实消费/真正花了多少/实际收入\"时,优先用 nature 参数过滤而非 type。"
        f"金额单位元。回答用中文,简洁。多条明细用 Markdown 表格输出(时间/商户/金额列),"
        f"重点数字加粗,不要罗列原始 JSON。数据有「成员」维度时可按成员对比。\n\n"
        "【图表】当数据适合可视化(趋势/对比/占比/排行)时,在回答中嵌入图表代码块,前端会渲染成交互图。格式:\n"
        "```chart\n"
        '{"type":"bar","title":"标题","categories":["1月","2月"],"series":[{"name":"支出","data":[100,200]}]}\n'
        "```\n"
        '类型:bar(对比/排行)、line(趋势)、pie(占比,用 "data":[{"name":"餐饮","value":123}] 代替 categories/series)。'
        "图表数据必须来自工具查询结果,每次回答最多 2 个图表;图表外仍配一两句结论文字。"
        "用户明确要求图表时必须输出;趋势/分布类问题主动配图。\n"
        "【导出文件】用户要导出/下载数据时,调用 export_transactions 工具(可选 xlsx/csv),"
        "然后在回答中用 Markdown 链接给出下载地址,如 [📥 下载 6月支出明细.xlsx](工具返回的url),并附笔数与金额合计。"
    )
    messages = []
    for h in (history or [])[-6:]:
        if h.get('role') in ('user', 'assistant') and h.get('content'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': question})

    tool_calls = []
    for _ in range(6):
        resp = _post_messages({
            'model': (cfg or {}).get('model') or AI_MODEL, 'max_tokens': 1500, 'system': system,
            'messages': messages, 'tools': ([_QUERY_TOOL, _OVERVIEW_TOOL, _EXPORT_TOOL] if uid else [_QUERY_TOOL, _OVERVIEW_TOOL]),
        }, cfg=cfg)
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
                if name == 'data_overview':
                    out = _run_overview(df)
                elif name == 'export_transactions' and uid:
                    out = _run_export(df, args, uid)
                else:
                    out = _run_query(df, args)
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


def recognize_bill(text_content, hint='', cfg=None):
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
        'model': (cfg or {}).get('model') or AI_MODEL, 'max_tokens': 4000, 'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    }, cfg=cfg)
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
