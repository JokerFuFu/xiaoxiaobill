"""
AI 对话历史存储(每用户独立)

存储:upload/<uid>/_ai_chats.json
结构:[{id, title, created_at, updated_at, messages:[{role, content, tools?}]}]
上限:50 个会话 / 每会话 200 条消息(超出裁旧),防止无限膨胀。
"""
import json
import logging
import os
import threading
from datetime import datetime
from secrets import token_hex

from config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)
_lock = threading.RLock()

MAX_CHATS = 50
MAX_MSGS = 200


def _file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_ai_chats.json')


def _load(uid):
    p = _file(uid)
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f) or []
    except Exception:
        logger.warning(f"_ai_chats.json 损坏,重置: {uid}")
        return []


def _save(uid, chats):
    p = _file(uid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(chats, f, ensure_ascii=False)
    os.replace(tmp, p)


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def list_chats(uid):
    """会话元数据列表(不含消息体),按更新时间倒序。"""
    chats = _load(uid)
    out = [{'id': c['id'], 'title': c.get('title', '新对话'),
            'updated_at': c.get('updated_at', ''), 'count': len(c.get('messages', []))}
           for c in chats]
    out.sort(key=lambda x: x['updated_at'], reverse=True)
    return out


def get_chat(uid, cid):
    for c in _load(uid):
        if c['id'] == cid:
            return c
    return None


def append_chat(uid, cid, user_content, assistant_content, tools=None):
    """把一轮问答追加到会话;cid 为空则新建会话(标题取首问前20字)。返回 cid。"""
    with _lock:
        chats = _load(uid)
        chat = next((c for c in chats if c['id'] == cid), None) if cid else None
        if chat is None:
            chat = {'id': 'c_' + token_hex(5),
                    'title': (user_content or '新对话').strip()[:20],
                    'created_at': _now(), 'messages': []}
            chats.append(chat)
        chat['messages'].append({'role': 'user', 'content': user_content})
        msg = {'role': 'assistant', 'content': assistant_content}
        if tools:
            msg['tools'] = tools
        chat['messages'].append(msg)
        chat['updated_at'] = _now()
        # 裁剪
        if len(chat['messages']) > MAX_MSGS:
            chat['messages'] = chat['messages'][-MAX_MSGS:]
        if len(chats) > MAX_CHATS:
            chats.sort(key=lambda c: c.get('updated_at', ''), reverse=True)
            chats = chats[:MAX_CHATS]
        _save(uid, chats)
        return chat['id']


def delete_chat(uid, cid):
    with _lock:
        chats = _load(uid)
        n = len(chats)
        chats = [c for c in chats if c['id'] != cid]
        if len(chats) == n:
            return False
        _save(uid, chats)
        return True


def history_for(uid, cid, limit=6):
    """取会话最近 limit 条消息作为模型上下文(role/content)。
    Anthropic 要求消息序列以 user 开头,切片后裁掉开头的 assistant。"""
    chat = get_chat(uid, cid) if cid else None
    if not chat:
        return []
    msgs = [{'role': m['role'], 'content': m['content']}
            for m in chat['messages'][-limit:] if m.get('content')]
    while msgs and msgs[0]['role'] != 'user':
        msgs.pop(0)
    return msgs
