"""
成员(人物)维度服务

每个用户空间内可记录多人(本人 + 家人等)的消费。成员不需要登录。
存储:upload/<uid>/_members.json(成员列表)+ _file_members.json(文件→成员映射)。
上传账单时整份归属到某成员,data_loader 给该文件的所有交易盖上「成员」列。
"""
import os
import json
import logging
import threading
from secrets import token_hex

from config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)
_lock = threading.RLock()

# 成员配色(轮转分配)
_COLORS = ['#007AFF', '#FF9500', '#34C759', '#AF52DE', '#FF2D55',
           '#5AC8FA', '#FFCC00', '#5856D6', '#FF3B30', '#30B0C7']


def _udir(uid):
    d = os.path.join(UPLOAD_FOLDER, uid)
    os.makedirs(d, exist_ok=True)
    return d


def _mfile(uid):
    return os.path.join(_udir(uid), '_members.json')


def _ffile(uid):
    return os.path.join(_udir(uid), '_file_members.json')


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def list_members(uid):
    """返回成员列表;若无则初始化一个默认成员「本人」。"""
    with _lock:
        ms = _load_json(_mfile(uid), None)
        if not ms:
            ms = [{'id': 'm_self', 'name': '本人', 'color': _COLORS[0], 'is_self': True}]
            _save_json(_mfile(uid), ms)
        return ms


def default_member_id(uid):
    ms = list_members(uid)
    for m in ms:
        if m.get('is_self'):
            return m['id']
    return ms[0]['id']


def member_name_map(uid):
    return {m['id']: m['name'] for m in list_members(uid)}


def add_member(uid, name, color=None):
    name = (name or '').strip()
    if not name:
        raise ValueError('成员名不能为空')
    with _lock:
        ms = list_members(uid)
        if any(m['name'] == name for m in ms):
            raise ValueError('成员已存在')
        color = color or _COLORS[len(ms) % len(_COLORS)]
        m = {'id': 'm_' + token_hex(3), 'name': name, 'color': color, 'is_self': False}
        ms.append(m)
        _save_json(_mfile(uid), ms)
        return m


def update_member(uid, member_id, name=None, color=None):
    with _lock:
        ms = list_members(uid)
        hit = next((m for m in ms if m['id'] == member_id), None)
        if not hit:
            raise ValueError('成员不存在')
        if name:
            name = name.strip()
            if any(m['name'] == name and m['id'] != member_id for m in ms):
                raise ValueError('成员名重复')
            hit['name'] = name
        if color:
            hit['color'] = color
        _save_json(_mfile(uid), ms)
        return hit


def delete_member(uid, member_id):
    """删除成员;该成员名下文件回落到默认成员。"""
    with _lock:
        ms = list_members(uid)
        hit = next((m for m in ms if m['id'] == member_id), None)
        if not hit:
            raise ValueError('成员不存在')
        if hit.get('is_self'):
            raise ValueError('不能删除「本人」成员')
        if len(ms) <= 1:
            raise ValueError('至少保留一个成员')
        ms = [m for m in ms if m['id'] != member_id]
        _save_json(_mfile(uid), ms)
        # 该成员名下文件回落到默认成员(本人),而非碰巧排首位的成员
        defm = next((m['id'] for m in ms if m.get('is_self')), ms[0]['id'])
        fm = get_file_member_map(uid)
        changed = False
        for fn, mid in list(fm.items()):
            if mid == member_id:
                fm[fn] = defm
                changed = True
        if changed:
            _save_json(_ffile(uid), fm)
        return True


def get_file_member_map(uid):
    return _load_json(_ffile(uid), {})


def set_file_member(uid, filename, member_id):
    with _lock:
        fm = get_file_member_map(uid)
        fm[filename] = member_id
        _save_json(_ffile(uid), fm)


def remove_file_member(uid, filename):
    with _lock:
        fm = get_file_member_map(uid)
        if filename in fm:
            del fm[filename]
            _save_json(_ffile(uid), fm)
