# 邮箱账单后台自动导入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让已配置好 IMAP 邮箱的用户开启"自动导入"后，后台每天自动扫描新账单邮件并完成能自动完成的导入，无需手动点击；无法自动解压的加密 zip 进入待处理队列，在设置页给出数量提示。

**Architecture:** 复用现有 `backend/services/mailbox.py` 里已跑通的 IMAP 连接、账单邮件识别（`fetch_bills`）、附件下载解析入库（`import_attachment`）——这两个函数本来就是纯 `uid` 参数传递、不依赖 Flask 请求上下文的设计，天然适合被后台线程直接调用。新增两层：①编排层（`auto_import_one`/`auto_import_all`）决定哪些附件能自动导入、哪些进待处理；②调度层（`APScheduler` `BackgroundScheduler`，挂在 `app.py` 启动流程里）定期触发编排层。所有新状态（自动导入开关、待处理队列、上次同步状态）沿用项目现有的"每用户一个 JSON 文件"存储风格，不引入数据库。

**Tech Stack:** Python 3.10 / Flask / APScheduler（新增依赖）/ pytest（新增依赖，项目此前无测试）/ Vue 3（前端 Settings.vue 局部改动，无新依赖）。

## Global Constraints

- 设计文档：[docs/superpowers/specs/2026-07-01-mail-auto-import-design.md](../specs/2026-07-01-mail-auto-import-design.md)，本计划的任何实现细节与设计文档冲突时以设计文档的产品决策为准。
- 调度周期默认 24 小时一次，通过环境变量 `MAIL_AUTO_IMPORT_INTERVAL_HOURS` 覆盖（运维参数，不在前端暴露）。
- 自动扫描邮件时间窗固定 35 天（覆盖"半月到一个月才传一次账单"的使用习惯），不做成用户可调项。
- 自动导入功能默认关闭（`auto_import: false`），需要用户在设置页显式开启；开启前必须已完整配置 host/address/授权码。
- 加密 zip 解压失败（主要是支付宝密码随机、无法自动获取）一律不重试、不猜测密码，记入待处理队列，等待用户手动补齐密码。
- 待处理队列文件 `_mail_pending.json` 上限 500 条，截断策略与现有 `_mail_imported.json` 一致（按最近时间保留）。
- 不做：微信/邮件推送通知、银行 PDF 解析器扩展、发件人→家庭成员自动映射规则。这些已在设计文档里明确排除。
- 所有新增代码注释、日志文案、UI 文案使用中文（项目 CLAUDE.md 规定）。
- 后端单进程运行（`app.py` 用 `app.run()`，非 gunicorn 多进程），调度器只需处理 Flask debug 重载器的父子进程问题，不需要跨进程分布式锁。

---

## 文件结构总览

**新增文件**
- `backend/conftest.py` —— 让 `backend/tests/` 下的测试能 `import services.mailbox` 等模块（本项目是扁平布局，没有 `backend` 这一层 package）。
- `backend/tests/conftest.py` —— 提供 `mail_uid` fixture：把 `services.mailbox.UPLOAD_FOLDER` 打到 `tmp_path`，实现测试间隔离，避免污染真实 `data/upload/`。
- `backend/tests/test_mailbox_pending.py` —— 待处理队列 + 自动同步状态文件读写的单元测试。
- `backend/tests/test_mailbox_config.py` —— `save_config`/`public_config` 新字段的单元测试。
- `backend/tests/test_mailbox_import.py` —— `import_attachment` 记录 attachment index + 清理待处理的单元测试。
- `backend/tests/test_mailbox_auto_import.py` —— `auto_import_one`/`auto_import_all` 编排逻辑的单元测试。
- `backend/tests/test_mailbox_scheduler.py` —— 调度器启动守卫函数的单元测试。
- `backend/tests/test_mail_api_validation.py` —— 开启自动导入前置校验函数的单元测试。
- `backend/tests/test_mailbox_fetch_bills.py` —— `fetch_bills` 附加 `needs_password` 标记的单元测试。

**修改文件**
- `backend/services/mailbox.py` —— 本次改动的主战场：待处理队列/状态文件读写、`import_attachment` 记账、`auto_import_one`/`auto_import_all` 编排、调度启动守卫函数、开启自动导入的校验函数、`fetch_bills` 附加标记、`save_config`/`public_config` 新字段。
- `backend/api/mail.py` —— `POST /api/mail/config` 支持读写 `auto_import` 字段并做前置校验。
- `backend/app.py` —— 启动时注册 `APScheduler` 定时任务。
- `backend/config.py` —— 新增 `MAIL_AUTO_IMPORT_INTERVAL_HOURS`。
- `backend/requirements.txt` —— 新增 `APScheduler`、`pytest`。
- `frontend/src/views/Settings.vue` —— 邮箱卡片新增"自动导入"开关、待处理角标、同步状态文案、附件"需要密码"提示。

**不需要改动**：`frontend/src/api/client.js`（`mailSaveConfig`/`mailGetConfig` 已是通用透传，新增字段自动生效，无需改代码）。

---

### Task 1: 待处理队列 + 自动同步状态文件读写（测试基础设施）

**Files:**
- Create: `backend/conftest.py`
- Create: `backend/tests/__init__.py`（空文件，占位即可）
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_mailbox_pending.py`
- Modify: `backend/services/mailbox.py`（文件末尾新增两个小节）
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces（后续任务都会用到）：
  - `_pending_file(uid) -> str`
  - `_load_pending(uid) -> dict`
  - `_save_pending(uid, data: dict) -> None`
  - `_mark_pending(uid, mail_uid: str, mail_meta: dict, att: dict) -> None`（`mail_meta` 需要 `subject`/`sender`/`date` 键，`att` 需要 `index`/`filename` 键——与 `fetch_bills()` 返回的邮件/附件字典结构完全一致）
  - `_clear_pending_index(uid, mail_uid, att_index) -> None`
  - `pending_count(uid) -> int`
  - `_status_file(uid) -> str`
  - `_load_auto_status(uid) -> dict`（键：`last_run_at`/`last_success_at`/`last_error`）
  - `_save_auto_status(uid, ok: bool, error: str = '') -> None`

- [ ] **Step 1: 创建 pytest 能找到模块的基础设施**

`backend/conftest.py`：

```python
"""
pytest 根 conftest —— 本项目是扁平布局(没有把 backend 做成 package),
测试需要能 import services.mailbox / config 等模块,这里显式把 backend/ 加进 sys.path。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

`backend/tests/__init__.py`：（空文件）

`backend/tests/conftest.py`：

```python
"""
邮箱自动导入相关测试的共享 fixture。
"""
import pytest

import services.mailbox as mailbox


@pytest.fixture
def mail_uid(tmp_path, monkeypatch):
    """把 mailbox 模块的 UPLOAD_FOLDER 打到临时目录,测试之间互不干扰,
    也不会碰到真实的 backend/data/upload/。返回一个测试用 uid 字符串。"""
    monkeypatch.setattr(mailbox, 'UPLOAD_FOLDER', str(tmp_path))
    return 'test_user'
```

- [ ] **Step 2: 写失败的测试（待处理队列）**

`backend/tests/test_mailbox_pending.py`：

```python
import services.mailbox as mailbox


def test_mark_pending_creates_entry_with_index_and_attachment():
    pass  # 占位,下一行开始写真正的用例


def test_mark_and_load_pending(mail_uid):
    uid = mail_uid
    mailbox._mark_pending(uid, '100', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'bill.zip'})
    pending = mailbox._load_pending(uid)
    assert pending['100']['indices'] == [0]
    assert pending['100']['attachments'] == [{'index': 0, 'filename': 'bill.zip'}]
    assert mailbox.pending_count(uid) == 1


def test_mark_pending_twice_same_index_does_not_duplicate(mail_uid):
    uid = mail_uid
    att = {'index': 0, 'filename': 'bill.zip'}
    meta = {'subject': 's', 'sender': 'x', 'date': 'd'}
    mailbox._mark_pending(uid, '100', meta, att)
    mailbox._mark_pending(uid, '100', meta, att)
    pending = mailbox._load_pending(uid)
    assert pending['100']['indices'] == [0]
    assert len(pending['100']['attachments']) == 1


def test_clear_pending_index_removes_entry_when_empty(mail_uid):
    uid = mail_uid
    mailbox._mark_pending(uid, '200', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 1, 'filename': 'a.zip'})
    assert mailbox.pending_count(uid) == 1
    mailbox._clear_pending_index(uid, '200', 1)
    assert mailbox.pending_count(uid) == 0
    assert mailbox._load_pending(uid) == {}


def test_clear_pending_index_keeps_other_indices(mail_uid):
    uid = mail_uid
    meta = {'subject': 's', 'sender': 'x', 'date': 'd'}
    mailbox._mark_pending(uid, '300', meta, {'index': 0, 'filename': 'a.zip'})
    mailbox._mark_pending(uid, '300', meta, {'index': 1, 'filename': 'b.zip'})
    mailbox._clear_pending_index(uid, '300', 0)
    pending = mailbox._load_pending(uid)
    assert pending['300']['indices'] == [1]


def test_save_pending_keeps_newest_500(mail_uid):
    uid = mail_uid
    data = {
        str(i): {'subject': 's', 'sender': 'x', 'date': 'd', 'indices': [0],
                 'attachments': [{'index': 0, 'filename': 'a.zip'}], 'seen_at': f'{i:05d}'}
        for i in range(510)
    }
    mailbox._save_pending(uid, data)
    loaded = mailbox._load_pending(uid)
    assert len(loaded) == 500
    assert set(loaded.keys()) == {str(i) for i in range(10, 510)}


def test_save_and_load_auto_status_records_error(mail_uid):
    uid = mail_uid
    mailbox._save_auto_status(uid, ok=False, error='登录失败:授权码可能已过期')
    status = mailbox._load_auto_status(uid)
    assert status['last_error'] == '登录失败:授权码可能已过期'
    assert status.get('last_success_at', '') == ''
    assert status['last_run_at']


def test_save_auto_status_success_clears_error(mail_uid):
    uid = mail_uid
    mailbox._save_auto_status(uid, ok=False, error='上一次失败')
    mailbox._save_auto_status(uid, ok=True)
    status = mailbox._load_auto_status(uid)
    assert status['last_error'] == ''
    assert status['last_success_at']
```

删掉上面那个占位的 `test_mark_pending_creates_entry_with_index_and_attachment`（写的时候留了个空壳提醒自己命名，实际不需要）。

- [ ] **Step 3: 运行测试，确认失败**

```bash
cd backend && pip install pytest && python -m pytest tests/test_mailbox_pending.py -v
```

预期：`AttributeError: module 'services.mailbox' has no attribute '_mark_pending'`（及其余用到的新函数）导致全部失败。

- [ ] **Step 4: 在 `backend/services/mailbox.py` 末尾追加实现**

在文件最后（`import_attachment` 函数之后）追加：

```python
# ============ 自动导入:待处理队列 ============
def _pending_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_mail_pending.json')


def _load_pending(uid):
    try:
        p = _pending_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save_pending(uid, data):
    # 只保留最近 500 条记录,策略与 _mail_imported.json 一致
    if len(data) > 500:
        items = sorted(data.items(), key=lambda kv: kv[1].get('seen_at', ''), reverse=True)
        data = dict(items[:500])
    p = _pending_file(uid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)


def _mark_pending(uid, mail_uid, mail_meta, att):
    """记一条"需要密码才能完成导入"的附件(通常是支付宝加密 zip)。"""
    with _mail_lock:
        pending = _load_pending(uid)
        key = str(mail_uid)
        rec = pending.setdefault(key, {
            'subject': mail_meta.get('subject', ''), 'sender': mail_meta.get('sender', ''),
            'date': mail_meta.get('date', ''), 'indices': [], 'attachments': [], 'seen_at': '',
        })
        idx = int(att['index'])
        if idx not in rec['indices']:
            rec['indices'].append(idx)
        if not any(a['index'] == idx for a in rec['attachments']):
            rec['attachments'].append({'index': idx, 'filename': att.get('filename', '')})
        rec['seen_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        _save_pending(uid, pending)


def _clear_pending_index(uid, mail_uid, att_index):
    """手动补齐密码导入成功后,把这个附件从待处理队列摘除。"""
    with _mail_lock:
        pending = _load_pending(uid)
        key = str(mail_uid)
        rec = pending.get(key)
        if not rec:
            return
        idx = int(att_index)
        rec['indices'] = [i for i in rec.get('indices', []) if i != idx]
        rec['attachments'] = [a for a in rec.get('attachments', []) if a['index'] != idx]
        if not rec['indices']:
            del pending[key]
        _save_pending(uid, pending)


def pending_count(uid):
    return sum(len(r.get('indices', [])) for r in _load_pending(uid).values())


# ============ 自动导入:健康状态 ============
def _status_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_mail_auto_status.json')


def _load_auto_status(uid):
    try:
        p = _status_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save_auto_status(uid, ok, error=''):
    """每次自动导入跑完(无论成功/部分失败/整体异常)都记一次,让用户能看到后台任务是否还活着。"""
    with _mail_lock:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = _load_auto_status(uid)
        status['last_run_at'] = now
        if ok:
            status['last_success_at'] = now
            status['last_error'] = ''
        else:
            status['last_error'] = str(error)[:200]
        p = _status_file(uid)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False)
        os.replace(tmp, p)
```

在 `backend/requirements.txt` 末尾追加：

```
# 测试
pytest>=7.4.0,<8.0.0
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/test_mailbox_pending.py -v
```

预期：全部 `PASSED`。

- [ ] **Step 6: Commit**

```bash
cd /Users/Apple/Projects/community/xiaoyaoprivatebill
git add backend/conftest.py backend/tests/__init__.py backend/tests/conftest.py \
        backend/tests/test_mailbox_pending.py backend/services/mailbox.py backend/requirements.txt
git commit -m "feat(mail): 邮箱自动导入——待处理队列与同步状态文件读写

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `save_config`/`public_config` 支持 `auto_import` 开关与状态字段

**Files:**
- Modify: `backend/services/mailbox.py`（`save_config`、`public_config` 两个已有函数）
- Create: `backend/tests/test_mailbox_config.py`

**Interfaces:**
- Consumes: `pending_count(uid)`、`_load_auto_status(uid)`（Task 1）
- Produces:
  - `save_config(uid, host=None, port=None, address=None, auth_code=None, auto_import=None) -> dict`（新增 `auto_import` 参数，`None` 表示不改）
  - `public_config(uid) -> dict`（返回体新增 `auto_import`/`pending_count`/`last_run_at`/`last_success_at`/`last_error`）

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_mailbox_config.py`：

```python
import services.mailbox as mailbox


def test_save_config_default_auto_import_is_false(mail_uid):
    uid = mail_uid
    cfg = mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')
    assert cfg['auto_import'] is False


def test_save_config_persists_auto_import_true(mail_uid):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')
    cfg = mailbox.save_config(uid, auto_import=True)
    assert cfg['auto_import'] is True


def test_save_config_without_auto_import_keeps_old_value(mail_uid):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code',
                        auto_import=True)
    cfg = mailbox.save_config(uid, port=993)
    assert cfg['auto_import'] is True


def test_public_config_exposes_auto_import_and_status_fields(mail_uid):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code',
                        auto_import=True)
    mailbox._mark_pending(uid, '1', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'a.zip'})
    mailbox._save_auto_status(uid, ok=False, error='测试错误')

    pub = mailbox.public_config(uid)
    assert pub['auto_import'] is True
    assert pub['pending_count'] == 1
    assert pub['last_error'] == '测试错误'
    assert pub['last_run_at']
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mailbox_config.py -v
```

预期：`KeyError: 'auto_import'` 一类的断言失败（`save_config`/`public_config` 还不认识这个字段）。

- [ ] **Step 3: 修改 `save_config`/`public_config`**

把现有 `save_config` 函数整体替换为：

```python
def save_config(uid, host=None, port=None, address=None, auth_code=None, auto_import=None):
    """auth_code: None=不改 / ''=清除 / 其他=替换。auto_import: None=不改。"""
    with _mail_lock:
        old = load_config(uid)
        new = {
            'host': str(host if host is not None else old.get('host', '')).strip()[:100],
            'port': int(port if port is not None else old.get('port', 993) or 993),
            'address': str(address if address is not None else old.get('address', '')).strip()[:100],
            'auth_code': ('' if auth_code == '' else
                          (str(auth_code).strip() if auth_code is not None else old.get('auth_code', ''))),
            'auto_import': bool(auto_import) if auto_import is not None else bool(old.get('auto_import', False)),
        }
        if new['port'] <= 0 or new['port'] > 65535:
            new['port'] = 993
        p = _cfg_file(uid)
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
```

把现有 `public_config` 函数整体替换为：

```python
def public_config(uid):
    cfg = load_config(uid)
    status = _load_auto_status(uid)
    return {
        'host': cfg.get('host', ''), 'port': cfg.get('port', 993),
        'address': cfg.get('address', ''),
        'has_auth': bool(cfg.get('auth_code')),
        'auto_import': bool(cfg.get('auto_import', False)),
        'pending_count': pending_count(uid),
        'last_run_at': status.get('last_run_at', ''),
        'last_success_at': status.get('last_success_at', ''),
        'last_error': status.get('last_error', ''),
        'presets': PRESETS,
    }
```

（`public_config` 原本定义在文件靠前的位置，`pending_count`/`_load_auto_status` 定义在文件末尾——Python 只在调用时查找函数名，不要求定义顺序，正常运行没问题。）

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/test_mailbox_config.py tests/test_mailbox_pending.py -v
```

预期：全部 `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add backend/services/mailbox.py backend/tests/test_mailbox_config.py
git commit -m "feat(mail): 邮箱配置支持 auto_import 开关 + 暴露待处理数量与同步状态

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `import_attachment` 记录附件序号 + 导入成功后清理待处理

**Files:**
- Modify: `backend/services/mailbox.py`（`import_attachment` 函数末尾）
- Create: `backend/tests/test_mailbox_import.py`

**Interfaces:**
- Consumes: `_clear_pending_index`、`_mark_pending`（Task 1）
- Produces: `import_attachment(...)` 签名不变，但 `_mail_imported.json` 里每条记录新增 `indices: [int, ...]` 字段；成功导入后会调用 `_clear_pending_index`。

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_mailbox_import.py`：

```python
import os

import services.mailbox as mailbox


class _DummyPart:
    def __init__(self, data):
        self._data = data

    def get_payload(self, decode=False):
        return self._data


def _setup_mail_env(uid, tmp_path, monkeypatch, filename='bill.csv', payload=b'a,b,c'):
    session_dir = os.path.join(str(tmp_path), uid)
    os.makedirs(session_dir, exist_ok=True)
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')

    class DummyM:
        def select(self, *a, **k):
            return ('OK', [b'1'])

        def logout(self):
            pass

    monkeypatch.setattr(mailbox, '_connect', lambda cfg: DummyM())
    monkeypatch.setattr(mailbox, '_fetch_msg', lambda M, mail_uid: object())
    monkeypatch.setattr(mailbox, '_iter_attachments',
                        lambda msg: [(0, filename, len(payload), _DummyPart(payload))])
    return session_dir


def test_import_attachment_records_index(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    session_dir = _setup_mail_env(uid, tmp_path, monkeypatch)

    result = mailbox.import_attachment(uid, '100', 0, session_dir=session_dir)

    assert result['files'] == ['bill.csv']
    imported = mailbox._load_imported(uid)
    assert imported['100']['indices'] == [0]


def test_import_attachment_clears_matching_pending_entry(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    session_dir = _setup_mail_env(uid, tmp_path, monkeypatch, filename='bill.zip')
    # 先假装这个附件之前需要密码、被记入待处理
    mailbox._mark_pending(uid, '100', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'bill.zip'})
    assert mailbox.pending_count(uid) == 1

    mailbox.import_attachment(uid, '100', 0, session_dir=session_dir)

    assert mailbox.pending_count(uid) == 0


def test_import_attachment_does_not_touch_other_mails_pending(mail_uid, tmp_path, monkeypatch):
    uid = mail_uid
    session_dir = _setup_mail_env(uid, tmp_path, monkeypatch)
    mailbox._mark_pending(uid, '999', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'other.zip'})

    mailbox.import_attachment(uid, '100', 0, session_dir=session_dir)

    assert mailbox.pending_count(uid) == 1  # 邮件 999 的待处理记录不受影响
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mailbox_import.py -v
```

预期：`test_import_attachment_records_index` 因为 `imported['100']` 没有 `'indices'` 键而 `KeyError`；`test_import_attachment_clears_matching_pending_entry` 因为 `pending_count` 导入后仍是 1 而断言失败。

- [ ] **Step 3: 修改 `import_attachment` 末尾的记账逻辑**

找到 `import_attachment` 函数里这一段（文件末尾附近）：

```python
    with _mail_lock:
        imported = _load_imported(uid)
        rec = imported.setdefault(str(mail_uid), {'files': [], 'at': ''})
        rec['files'] = sorted(set(rec['files'] + saved))
        rec['at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        _save_imported(uid, imported)

    logger.info(f"邮箱导入 {len(saved)} 个账单文件: {saved}")
    return {'files': saved}
```

替换为：

```python
    with _mail_lock:
        imported = _load_imported(uid)
        rec = imported.setdefault(str(mail_uid), {'files': [], 'at': '', 'indices': []})
        rec['files'] = sorted(set(rec['files'] + saved))
        rec.setdefault('indices', [])
        rec['indices'] = sorted(set(rec['indices'] + [int(att_index)]))
        rec['at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        _save_imported(uid, imported)
    _clear_pending_index(uid, mail_uid, int(att_index))

    logger.info(f"邮箱导入 {len(saved)} 个账单文件: {saved}")
    return {'files': saved}
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/ -v
```

预期：全部 `PASSED`（包括 Task 1/2 的测试，确认没有回归）。

- [ ] **Step 5: Commit**

```bash
git add backend/services/mailbox.py backend/tests/test_mailbox_import.py
git commit -m "feat(mail): 附件导入记录序号并清理对应待处理记录

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `auto_import_one` —— 单用户自动导入编排逻辑

**Files:**
- Modify: `backend/services/mailbox.py`（文件末尾新增一节）
- Create: `backend/tests/test_mailbox_auto_import.py`

**Interfaces:**
- Consumes: `fetch_bills(uid, days)`（已有）、`import_attachment(uid, mail_uid, att_index, zip_password=None, member_id=None, session_dir=None)`（已有，Task 3 已扩展）、`_load_imported`/`_save_imported`（已有）、`_load_pending`/`_mark_pending`（Task 1）、`_save_auto_status`（Task 1）
- Produces:
  - `AUTO_IMPORT_WINDOW_DAYS = 35`（模块级常量）
  - `auto_import_one(uid, days=None) -> {'imported': int, 'pending': int, 'error': str | None}`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_mailbox_auto_import.py`：

```python
import services.mailbox as mailbox


def _fake_mail(mail_uid, attachments):
    return {'uid': mail_uid, 'subject': 's', 'sender': 'x', 'date': 'd',
            'attachments': attachments, 'imported_files': []}


def test_auto_import_one_imports_non_password_attachment(mail_uid, monkeypatch):
    uid = mail_uid
    mail = _fake_mail('1', [{'index': 0, 'filename': 'bill.csv', 'size': 10, 'is_zip': False}])
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])
    calls = []

    def fake_import(u, mail_uid, idx, zip_password=None, member_id=None, session_dir=None):
        calls.append((mail_uid, idx))
        return {'files': ['bill.csv']}

    monkeypatch.setattr(mailbox, 'import_attachment', fake_import)

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 1, 'pending': 0, 'error': None}
    assert calls == [('1', 0)]


def test_auto_import_one_marks_encrypted_zip_as_pending(mail_uid, monkeypatch):
    uid = mail_uid
    mail = _fake_mail('2', [{'index': 0, 'filename': 'bill.zip', 'size': 10, 'is_zip': True}])
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])

    def fake_import(u, mail_uid, idx, zip_password=None, member_id=None, session_dir=None):
        raise ValueError('压缩包密码错误或未提供(支付宝/微信的账单包需要密码)')

    monkeypatch.setattr(mailbox, 'import_attachment', fake_import)

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 0, 'pending': 1, 'error': None}
    assert mailbox.pending_count(uid) == 1


def test_auto_import_one_skips_already_done_and_already_pending(mail_uid, monkeypatch):
    uid = mail_uid
    mail = _fake_mail('3', [
        {'index': 0, 'filename': 'a.csv', 'size': 10, 'is_zip': False},
        {'index': 1, 'filename': 'b.zip', 'size': 10, 'is_zip': True},
    ])
    monkeypatch.setattr(mailbox, 'fetch_bills', lambda u, days=90: [mail])

    imported = mailbox._load_imported(uid)
    imported['3'] = {'files': ['a.csv'], 'at': 'x', 'indices': [0]}
    mailbox._save_imported(uid, imported)
    mailbox._mark_pending(uid, '3', mail, mail['attachments'][1])

    calls = []
    monkeypatch.setattr(mailbox, 'import_attachment',
                        lambda *a, **k: calls.append(a) or {'files': []})

    result = mailbox.auto_import_one(uid)

    assert result == {'imported': 0, 'pending': 0, 'error': None}
    assert calls == []


def test_auto_import_one_records_error_when_fetch_fails(mail_uid, monkeypatch):
    uid = mail_uid

    def boom(u, days=90):
        raise ValueError('邮箱未配置完整(服务器/邮箱地址/授权码)')

    monkeypatch.setattr(mailbox, 'fetch_bills', boom)

    result = mailbox.auto_import_one(uid)

    assert result['imported'] == 0
    assert '邮箱未配置完整' in result['error']
    status = mailbox._load_auto_status(uid)
    assert '邮箱未配置完整' in status['last_error']
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mailbox_auto_import.py -v
```

预期：`AttributeError: module 'services.mailbox' has no attribute 'auto_import_one'`。

- [ ] **Step 3: 在 `backend/services/mailbox.py` 末尾追加实现**

```python
# ============ 自动导入:编排逻辑 ============
AUTO_IMPORT_WINDOW_DAYS = 35  # 覆盖"半月到一个月才传一次账单"的使用习惯


def auto_import_one(uid, days=None):
    """对单个用户跑一轮自动导入。
    能自动解压/解析的附件(银行 PDF、未加密 zip、csv/xlsx)直接导入;
    加密 zip 解压失败(典型是支付宝密码随机、机器拿不到)不重试,记入待处理队列。
    返回 {'imported': 本轮新导入的附件数, 'pending': 本轮新记入待处理的附件数, 'error': 失败原因或 None}。"""
    days = days or AUTO_IMPORT_WINDOW_DAYS
    session_dir = os.path.join(UPLOAD_FOLDER, uid)
    try:
        mails = fetch_bills(uid, days=days)
    except Exception as e:
        logger.warning(f"自动导入拉取邮件失败: uid={uid} err={e}")
        _save_auto_status(uid, ok=False, error=str(e))
        return {'imported': 0, 'pending': 0, 'error': str(e)}

    imported_map = _load_imported(uid)
    pending_map = _load_pending(uid)
    imported_count = 0
    pending_new = 0

    for m in mails:
        mail_uid = m['uid']
        done_idx = set(imported_map.get(mail_uid, {}).get('indices', []))
        pend_idx = set(pending_map.get(mail_uid, {}).get('indices', []))
        for a in m['attachments']:
            idx = a['index']
            if idx in done_idx or idx in pend_idx:
                continue
            try:
                import_attachment(uid, mail_uid, idx, zip_password=None, member_id=None,
                                   session_dir=session_dir)
                imported_count += 1
            except ValueError:
                if a.get('is_zip'):
                    _mark_pending(uid, mail_uid, m, a)
                    pending_new += 1
                else:
                    logger.warning(
                        f"自动导入跳过附件(非密码类失败): uid={uid} mail_uid={mail_uid} idx={idx}")
            except Exception:
                logger.exception(f"自动导入附件异常: uid={uid} mail_uid={mail_uid} idx={idx}")

    _save_auto_status(uid, ok=True)
    return {'imported': imported_count, 'pending': pending_new, 'error': None}
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/ -v
```

预期：全部 `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add backend/services/mailbox.py backend/tests/test_mailbox_auto_import.py
git commit -m "feat(mail): 单用户自动导入编排逻辑 auto_import_one

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `auto_import_all` —— 遍历全部用户 + 失败隔离

**Files:**
- Modify: `backend/services/mailbox.py`（文件末尾新增）
- Modify: `backend/tests/test_mailbox_auto_import.py`（追加用例）

**Interfaces:**
- Consumes: `auto_import_one(uid)`（Task 4）、`load_config(uid)`（已有）、`services.auth.list_users()`（已有，返回 `[{'id': uid, ...}, ...]`）
- Produces: `auto_import_all() -> None`

- [ ] **Step 1: 写失败的测试**

在 `backend/tests/test_mailbox_auto_import.py` 末尾追加：

```python
import services.auth as auth


def test_auto_import_all_skips_disabled_and_isolates_failures(mail_uid, monkeypatch):
    monkeypatch.setattr(auth, 'list_users', lambda: [
        {'id': 'u1'}, {'id': 'u2'}, {'id': 'u3'},
    ])
    mailbox.save_config('u1', host='imap.qq.com', port=993, address='a@qq.com', auth_code='c',
                        auto_import=True)
    mailbox.save_config('u2', host='imap.qq.com', port=993, address='b@qq.com', auth_code='c',
                        auto_import=True)
    mailbox.save_config('u3', host='imap.qq.com', port=993, address='c@qq.com', auth_code='c',
                        auto_import=False)

    calls = []

    def fake_auto_import_one(uid, days=None):
        calls.append(uid)
        if uid == 'u1':
            raise RuntimeError('模拟 u1 自动导入崩了')
        return {'imported': 0, 'pending': 0, 'error': None}

    monkeypatch.setattr(mailbox, 'auto_import_one', fake_auto_import_one)

    mailbox.auto_import_all()

    assert calls == ['u1', 'u2']
    status_u1 = mailbox._load_auto_status('u1')
    assert '异常' in status_u1['last_error']
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mailbox_auto_import.py -v
```

预期：`AttributeError: module 'services.mailbox' has no attribute 'auto_import_all'`。

- [ ] **Step 3: 在 `backend/services/mailbox.py` 末尾追加实现**

```python
def auto_import_all():
    """后台定时任务入口:遍历全部用户,只处理开启了自动导入的;单个用户异常不影响其他用户。"""
    from services.auth import list_users
    for u in list_users():
        uid = u['id']
        cfg = load_config(uid)
        if not cfg.get('auto_import'):
            continue
        try:
            auto_import_one(uid)
        except Exception:
            logger.exception(f"自动导入用户 {uid} 执行异常")
            _save_auto_status(uid, ok=False, error='自动导入执行异常,请查看后端日志')
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/ -v
```

预期：全部 `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add backend/services/mailbox.py backend/tests/test_mailbox_auto_import.py
git commit -m "feat(mail): 遍历全部用户执行自动导入,单用户异常互不影响

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: 调度器启动守卫 + `app.py` 接入 APScheduler

**Files:**
- Modify: `backend/services/mailbox.py`（新增一个纯函数）
- Modify: `backend/config.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/app.py`
- Create: `backend/tests/test_mailbox_scheduler.py`

**Interfaces:**
- Consumes: `auto_import_all`（Task 5）
- Produces: `should_start_mail_scheduler(debug: bool, werkzeug_run_main: str | None) -> bool`；`config.MAIL_AUTO_IMPORT_INTERVAL_HOURS: int`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_mailbox_scheduler.py`：

```python
import services.mailbox as mailbox


def test_should_start_scheduler_in_production_single_process():
    assert mailbox.should_start_mail_scheduler(debug=False, werkzeug_run_main=None) is True


def test_should_start_scheduler_debug_parent_process_skips():
    assert mailbox.should_start_mail_scheduler(debug=True, werkzeug_run_main=None) is False


def test_should_start_scheduler_debug_reloader_child_starts():
    assert mailbox.should_start_mail_scheduler(debug=True, werkzeug_run_main='true') is True
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mailbox_scheduler.py -v
```

预期：`AttributeError: module 'services.mailbox' has no attribute 'should_start_mail_scheduler'`。

- [ ] **Step 3: 在 `backend/services/mailbox.py` 末尾追加实现**

```python
def should_start_mail_scheduler(debug, werkzeug_run_main):
    """决定当前进程是否应该启动后台定时任务。
    生产环境(debug=False)只有一个进程,直接启动;开发环境 Flask debug 模式下
    reloader 会额外起一个子进程,只在真正对外服务的子进程(WERKZEUG_RUN_MAIN=='true')里启动,
    避免同一台机器上跑出两份定时任务。"""
    return (not debug) or werkzeug_run_main == 'true'
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/test_mailbox_scheduler.py -v
```

预期：全部 `PASSED`。

- [ ] **Step 5: 新增配置项与依赖**

在 `backend/config.py` 末尾追加：

```python
# ============ 邮箱账单自动导入 ============
MAIL_AUTO_IMPORT_INTERVAL_HOURS = int(os.environ.get('MAIL_AUTO_IMPORT_INTERVAL_HOURS', '24'))
```

在 `backend/requirements.txt` 末尾追加：

```
# 邮箱自动导入:后台定时任务
APScheduler>=3.10.0,<4.0.0
```

- [ ] **Step 6: 在 `backend/app.py` 接入调度器**

在 `app.py` 里找到这两行（"启动时初始化"小节）：

```python
ensure_upload_dir()
ensure_admin()  # 首次启动 bootstrap 管理员(uid=user_local,保留既有数据)
```

在它们下面追加：

```python

# ============ 邮箱账单后台自动导入 ============
from services.mailbox import should_start_mail_scheduler, auto_import_all
from config import MAIL_AUTO_IMPORT_INTERVAL_HOURS

if should_start_mail_scheduler(DEBUG, os.environ.get('WERKZEUG_RUN_MAIN')):
    from apscheduler.schedulers.background import BackgroundScheduler
    import atexit

    _mail_scheduler = BackgroundScheduler(daemon=True)
    _mail_scheduler.add_job(auto_import_all, 'interval', hours=MAIL_AUTO_IMPORT_INTERVAL_HOURS,
                             id='mail_auto_import', misfire_grace_time=3600)
    _mail_scheduler.start()
    atexit.register(lambda: _mail_scheduler.shutdown(wait=False))
    logger.info(f"邮箱自动导入定时任务已启动,每 {MAIL_AUTO_IMPORT_INTERVAL_HOURS} 小时执行一次")
```

- [ ] **Step 7: 手动验证 app 能正常启动且只注册一次任务**

安装新依赖并启动一次（生产模式，`config.py` 里 `DEBUG` 当前硬编码为 `True`——如果保持默认，会走"开发模式"分支；为了验证生产分支，可以直接改 `config.py` 里 `DEBUG = False` 跑一次，验证完记得改回来，这不是本任务要修的既有问题）：

```bash
cd backend && pip install -r requirements.txt
python app.py
```

预期日志里出现且只出现一次：

```
邮箱自动导入定时任务已启动,每 24 小时执行一次
```

用 `Ctrl+C` 停止，确认没有报错堆栈。

- [ ] **Step 8: Commit**

```bash
git add backend/services/mailbox.py backend/config.py backend/requirements.txt backend/app.py \
        backend/tests/test_mailbox_scheduler.py
git commit -m "feat(mail): 接入 APScheduler 定时执行邮箱自动导入

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: API 层——开启自动导入前的完整性校验

**Files:**
- Modify: `backend/services/mailbox.py`（新增一个纯函数）
- Modify: `backend/api/mail.py`（`save_config` 路由）
- Create: `backend/tests/test_mail_api_validation.py`

**Interfaces:**
- Consumes: `load_config`/`save_config`/`public_config`（已有/Task 2）
- Produces: `validate_auto_import_request(auto_import: bool, final_host: str, final_address: str, final_auth: str) -> str | None`（返回错误信息，合法时返回 `None`）

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_mail_api_validation.py`：

```python
import services.mailbox as mailbox


def test_validate_auto_import_request_blocks_when_incomplete():
    err = mailbox.validate_auto_import_request(True, '', 'a@qq.com', 'code')
    assert err == '请先完整配置邮箱(服务器/地址/授权码)再开启自动导入'


def test_validate_auto_import_request_allows_when_complete():
    assert mailbox.validate_auto_import_request(True, 'imap.qq.com', 'a@qq.com', 'code') is None


def test_validate_auto_import_request_ignores_when_turning_off():
    assert mailbox.validate_auto_import_request(False, '', '', '') is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mail_api_validation.py -v
```

预期：`AttributeError: module 'services.mailbox' has no attribute 'validate_auto_import_request'`。

- [ ] **Step 3: 在 `backend/services/mailbox.py` 末尾追加实现**

```python
def validate_auto_import_request(auto_import, final_host, final_address, final_auth):
    """校验"即将生效"的邮箱配置是否足够开启自动导入;合法返回 None,否则返回错误提示。"""
    if not auto_import:
        return None
    if not (final_host and final_address and final_auth):
        return '请先完整配置邮箱(服务器/地址/授权码)再开启自动导入'
    return None
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/test_mail_api_validation.py -v
```

预期：全部 `PASSED`。

- [ ] **Step 5: 修改 `backend/api/mail.py` 的 `save_config` 路由**

把现有：

```python
@mail_bp.route('/api/mail/config', methods=['POST'])
def save_config():
    data = request.get_json(silent=True) or {}
    host = (data.get('host') or '').strip()
    address = (data.get('address') or '').strip()
    if host and not all(c.isalnum() or c in '.-' for c in host):
        return jsonify({'success': False, 'error': '服务器地址格式不对'}), 400
    if address and '@' not in address:
        return jsonify({'success': False, 'error': '邮箱地址格式不对'}), 400
    mail_svc.save_config(_uid(), host=host or None, port=data.get('port'),
                         address=address or None, auth_code=data.get('auth_code'))
    return jsonify({'success': True, 'config': mail_svc.public_config(_uid())})
```

替换为：

```python
@mail_bp.route('/api/mail/config', methods=['POST'])
def save_config():
    data = request.get_json(silent=True) or {}
    host = (data.get('host') or '').strip()
    address = (data.get('address') or '').strip()
    if host and not all(c.isalnum() or c in '.-' for c in host):
        return jsonify({'success': False, 'error': '服务器地址格式不对'}), 400
    if address and '@' not in address:
        return jsonify({'success': False, 'error': '邮箱地址格式不对'}), 400

    uid = _uid()
    auto_import = bool(data.get('auto_import'))
    cur = mail_svc.load_config(uid)
    final_host = host or cur.get('host', '')
    final_address = address or cur.get('address', '')
    final_auth = data.get('auth_code') or cur.get('auth_code', '')
    err = mail_svc.validate_auto_import_request(auto_import, final_host, final_address, final_auth)
    if err:
        return jsonify({'success': False, 'error': err}), 400

    mail_svc.save_config(uid, host=host or None, port=data.get('port'),
                         address=address or None, auth_code=data.get('auth_code'),
                         auto_import=(bool(data.get('auto_import')) if 'auto_import' in data else None))
    return jsonify({'success': True, 'config': mail_svc.public_config(uid)})
```

- [ ] **Step 6: 运行全部后端测试，确认没有回归**

```bash
cd backend && python -m pytest tests/ -v
```

预期：全部 `PASSED`。

- [ ] **Step 7: Commit**

```bash
git add backend/services/mailbox.py backend/api/mail.py backend/tests/test_mail_api_validation.py
git commit -m "feat(mail): API 层校验——配置不完整时禁止开启自动导入

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: `fetch_bills` 附加 `needs_password` 标记

**Files:**
- Modify: `backend/services/mailbox.py`（`fetch_bills` 函数）
- Create: `backend/tests/test_mailbox_fetch_bills.py`

**Interfaces:**
- Consumes: `_load_pending`（Task 1）
- Produces: `fetch_bills(uid, days=90)` 返回的每个 `attachments` 项新增布尔字段 `needs_password`

- [ ] **Step 1: 写失败的测试**

`backend/tests/test_mailbox_fetch_bills.py`：

```python
import services.mailbox as mailbox


class _DummyImap:
    def __init__(self, search_uids, header_map):
        self._search_uids = search_uids
        self._header_map = header_map

    def select(self, *a, **k):
        return ('OK', [b'1'])

    def uid(self, cmd, *args):
        if cmd == 'SEARCH':
            return ('OK', [self._search_uids])
        if cmd == 'FETCH':
            mail_uid_arg = args[0]
            query = args[1] if len(args) > 1 else ''
            if 'HEADER.FIELDS' in query:
                resp = []
                for one in mail_uid_arg.split(b','):
                    hdr = self._header_map.get(one)
                    if hdr is not None:
                        resp.append((b'%s (UID %s BODY[HEADER.FIELDS] {%d}' % (one, one, len(hdr)), hdr))
                return ('OK', resp)
            return ('OK', [(b'', b'')])
        raise AssertionError(f'unexpected uid() call: {cmd} {args}')

    def logout(self):
        pass


def test_fetch_bills_marks_needs_password_for_pending_attachment(mail_uid, monkeypatch):
    uid = mail_uid
    mailbox.save_config(uid, host='imap.qq.com', port=993, address='a@qq.com', auth_code='code')

    header = b'Subject: Test\r\nFrom: alipay@alipay.com\r\nDate: Mon, 1 Jun 2026 08:00:00 +0800\r\n\r\n'
    dummy = _DummyImap(search_uids=b'100', header_map={b'100': header})
    monkeypatch.setattr(mailbox, '_connect', lambda cfg: dummy)
    monkeypatch.setattr(mailbox, '_fetch_msg', lambda M, mail_uid: object())
    monkeypatch.setattr(mailbox, '_iter_attachments', lambda msg: [
        (0, 'bill.zip', 1000, object()),
        (1, 'other.csv', 200, object()),
    ])

    mailbox._mark_pending(uid, '100', {'subject': 's', 'sender': 'x', 'date': 'd'},
                          {'index': 0, 'filename': 'bill.zip'})

    mails = mailbox.fetch_bills(uid, days=90)

    assert len(mails) == 1
    atts = {a['index']: a for a in mails[0]['attachments']}
    assert atts[0]['needs_password'] is True
    assert atts[1]['needs_password'] is False
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_mailbox_fetch_bills.py -v
```

预期：`KeyError: 'needs_password'`。

- [ ] **Step 3: 修改 `fetch_bills`**

找到 `fetch_bills` 函数里这一段：

```python
        imported = _load_imported(uid)
        results = []
        for u, subject, sender, date_raw in candidates:
            try:
                msg = _fetch_msg(M, u)
            except Exception:
                continue
            atts = _iter_attachments(msg)
            if not atts:
                continue
            try:
                dt = email.utils.parsedate_to_datetime(date_raw)
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                date_str = str(date_raw)[:25]
            rec = imported.get(u.decode())
            results.append({
                'uid': u.decode(),
                'subject': subject[:80] or '(无主题)',
                'sender': sender[:60],
                'date': date_str,
                'attachments': [{'index': i, 'filename': fn, 'size': sz,
                                 'is_zip': fn.lower().endswith('.zip')}
                                for i, fn, sz, _ in atts],
                'imported_files': (rec or {}).get('files', []),
            })
        return results
```

替换为：

```python
        imported = _load_imported(uid)
        pending = _load_pending(uid)
        results = []
        for u, subject, sender, date_raw in candidates:
            try:
                msg = _fetch_msg(M, u)
            except Exception:
                continue
            atts = _iter_attachments(msg)
            if not atts:
                continue
            try:
                dt = email.utils.parsedate_to_datetime(date_raw)
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                date_str = str(date_raw)[:25]
            rec = imported.get(u.decode())
            pend_idx = set(pending.get(u.decode(), {}).get('indices', []))
            results.append({
                'uid': u.decode(),
                'subject': subject[:80] or '(无主题)',
                'sender': sender[:60],
                'date': date_str,
                'attachments': [{'index': i, 'filename': fn, 'size': sz,
                                 'is_zip': fn.lower().endswith('.zip'),
                                 'needs_password': i in pend_idx}
                                for i, fn, sz, _ in atts],
                'imported_files': (rec or {}).get('files', []),
            })
        return results
```

- [ ] **Step 4: 运行全部后端测试，确认通过且无回归**

```bash
cd backend && python -m pytest tests/ -v
```

预期：全部 `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add backend/services/mailbox.py backend/tests/test_mailbox_fetch_bills.py
git commit -m "feat(mail): 拉取邮件列表时标记需要密码的待处理附件

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: 前端——自动导入开关、待处理角标、同步状态、需要密码提示

**Files:**
- Modify: `frontend/src/views/Settings.vue`

**Interfaces:**
- Consumes: `api.mailGetConfig()`/`api.mailSaveConfig(payload)`（已有，无需改动，`payload` 直接透传新字段）；后端返回的 `config` 对象新增 `auto_import`/`pending_count`/`last_run_at`/`last_success_at`/`last_error` 字段（Task 2/7），`mails[].attachments[].needs_password` 字段（Task 8）
- Produces: 无新对外接口，纯 UI

本任务前后端都已就绪、无新增后端逻辑，只做界面接线，不写自动化测试（项目前端目前没有配置任何测试框架/测试脚本，`package.json` 里只有 `dev`/`build`/`preview`，引入 Vitest 属于超出本次范围的基础设施改动）。改完后用手动浏览器验证收尾。

- [ ] **Step 1: 扩展 `mailCfg` 初始值 + 新增 `mailAutoImport` ref**

在 `frontend/src/views/Settings.vue` 里找到：

```javascript
const mailCfg = ref({ host: '', port: 993, address: '', has_auth: false, presets: [] })
const mailForm = ref({ host: '', port: 993, address: '', auth_code: '' })
```

替换为：

```javascript
const mailCfg = ref({ host: '', port: 993, address: '', has_auth: false, presets: [],
                       auto_import: false, pending_count: 0, last_run_at: '', last_success_at: '', last_error: '' })
const mailForm = ref({ host: '', port: 993, address: '', auth_code: '' })
const mailAutoImport = ref(false)
```

- [ ] **Step 2: `loadMailConfig` 同步开关状态 + 新增 `toggleAutoImport`**

找到：

```javascript
async function loadMailConfig() {
  try {
    const r = await api.mailGetConfig()
    mailCfg.value = r.config
    mailForm.value.host = r.config.host || ''
    mailForm.value.port = r.config.port || 993
    mailForm.value.address = r.config.address || ''
    mailForm.value.auth_code = ''
  } catch (e) { /* 未登录等场景忽略 */ }
}
```

替换为：

```javascript
async function loadMailConfig() {
  try {
    const r = await api.mailGetConfig()
    mailCfg.value = r.config
    mailForm.value.host = r.config.host || ''
    mailForm.value.port = r.config.port || 993
    mailForm.value.address = r.config.address || ''
    mailForm.value.auth_code = ''
    mailAutoImport.value = !!r.config.auto_import
  } catch (e) { /* 未登录等场景忽略 */ }
}

async function toggleAutoImport() {
  const next = mailAutoImport.value
  try {
    const r = await api.mailSaveConfig({ auto_import: next })
    mailCfg.value = r.config
    uiStore.showSuccess(next ? '已开启自动导入' : '已关闭自动导入')
  } catch (e) {
    mailAutoImport.value = !next
    uiStore.showError(e.message || '设置失败')
  }
}
```

- [ ] **Step 3: 模板里加开关 + 角标 + 状态文案**

找到（`<!-- 拉取与导入 -->` 之前的那个 `<div class="cfg-actions">` 结束标签）：

```html
        <div class="cfg-actions">
          <button class="save-btn" @click="saveMailConfig" :disabled="!!mailBusy">
            <i class="fas fa-check"></i> 保存配置
          </button>
          <button class="test-btn" @click="testMail" :disabled="!!mailBusy">
            <i class="fas fa-plug"></i> {{ mailBusy === 'test' ? '测试中…' : '测试连接' }}
          </button>
          <button v-if="mailCfg.has_auth" class="reset-btn" @click="clearMailAuth" :disabled="!!mailBusy">清除授权码</button>
          <span v-if="mailTestMsg" class="test-result" :class="{ ok: mailTestOk }">
            <i :class="mailTestOk ? 'fas fa-circle-check' : 'fas fa-circle-xmark'"></i> {{ mailTestMsg }}
          </span>
        </div>

        <!-- 拉取与导入 -->
```

替换为：

```html
        <div class="cfg-actions">
          <button class="save-btn" @click="saveMailConfig" :disabled="!!mailBusy">
            <i class="fas fa-check"></i> 保存配置
          </button>
          <button class="test-btn" @click="testMail" :disabled="!!mailBusy">
            <i class="fas fa-plug"></i> {{ mailBusy === 'test' ? '测试中…' : '测试连接' }}
          </button>
          <button v-if="mailCfg.has_auth" class="reset-btn" @click="clearMailAuth" :disabled="!!mailBusy">清除授权码</button>
          <span v-if="mailTestMsg" class="test-result" :class="{ ok: mailTestOk }">
            <i :class="mailTestOk ? 'fas fa-circle-check' : 'fas fa-circle-xmark'"></i> {{ mailTestMsg }}
          </span>
        </div>

        <div class="cfg-actions" style="margin-top:8px">
          <label class="switch">
            <input type="checkbox" v-model="mailAutoImport" :disabled="!mailCfg.has_auth" @change="toggleAutoImport" />
            <span class="slider"></span>
          </label>
          <span>{{ mailAutoImport ? '自动导入已开启' : '自动导入已关闭' }}</span>
          <span v-if="mailCfg.pending_count" class="cfg-badge custom">{{ mailCfg.pending_count }} 封待导入(需要密码)</span>
          <span v-if="mailCfg.last_error" class="test-result">
            <i class="fas fa-circle-xmark"></i> 自动同步失败:{{ mailCfg.last_error }}
          </span>
          <span v-else-if="mailCfg.last_success_at" class="muted">上次自动同步:{{ mailCfg.last_success_at }}</span>
        </div>

        <!-- 拉取与导入 -->
```

- [ ] **Step 4: 邮件列表里给需要密码的附件加提示**

找到：

```html
            <div v-for="a in m.attachments" :key="a.index" class="mail-att">
              <i :class="a.is_zip ? 'fas fa-file-zipper' : 'fas fa-file-lines'"></i>
              <span class="att-name">{{ a.filename }}</span>
              <span class="att-size">{{ fmtSize(a.size) }}</span>
              <input
```

替换为：

```html
            <div v-for="a in m.attachments" :key="a.index" class="mail-att">
              <i :class="a.is_zip ? 'fas fa-file-zipper' : 'fas fa-file-lines'"></i>
              <span class="att-name">{{ a.filename }}</span>
              <span class="att-size">{{ fmtSize(a.size) }}</span>
              <span v-if="a.needs_password" class="cfg-badge default">需要密码</span>
              <input
```

- [ ] **Step 5: 手动浏览器验证**

```bash
cd backend && python app.py &
cd frontend && npm run dev
```

在浏览器里：
1. 登录后进入 设置 → 账单文件 tab，滚动到"从邮箱导入账单"卡片。
2. 确认新开关"自动导入"显示为关闭态，且在未配置邮箱（`has_auth` 为 false）时开关是禁用状态。
3. 用一个真实/测试 IMAP 邮箱填好地址+授权码，点"保存配置"、"测试连接"确认成功。
4. 打开"自动导入"开关，确认提示"已开启自动导入"，页面刷新后开关状态保持。
5. 关掉浏览器控制台里没有报错（用浏览器开发者工具或 Preview 工具的 console 检查）。
6. 点"拉取账单邮件"，如果邮箱里有之前被标记为待处理的加密 zip，确认对应附件行会显示"需要密码"标签。
7. 手动跑一轮自动导入模拟定时任务触发：
   ```bash
   cd backend && python -c "from services.mailbox import auto_import_all; auto_import_all()"
   ```
   刷新设置页，确认"上次自动同步"文案更新、待处理角标数字符合预期、"交易记录"里能看到新自动导入的账单（如果邮箱里确实有可自动导入的新账单）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/Settings.vue
git commit -m "feat(mail): 设置页新增自动导入开关/待处理角标/同步状态提示

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review 记录

- **Spec 覆盖**：设计文档 3.1(开关)→Task2/7/9；3.2(调度+自动导入判定)→Task4/5/6；3.3(待处理队列与角标)→Task1/3/8/9；3.4(健壮性可见性)→Task1/2/5/9；3.5(成员归属)→Task4 里 `member_id=None` 直接复用现有默认行为，无需新代码；3.6(去重)→说明性质，已在 Task4 注释中体现"不重复尝试已完成/已知待处理的附件"，交易级去重完全复用现有 `data_loader.py`，未新增任务，符合设计文档"不新增机制"的表述。
- **占位符扫描**：全文没有 TBD/"待补充"/"添加适当的错误处理"这类占位描述，每个 Step 都给了完整代码或精确到字节的手动验证命令与预期输出。
- **类型/签名一致性**：`auto_import_one` 在 Task 4 定义为 `(uid, days=None) -> {'imported','pending','error'}`，Task 5/9 引用时保持一致；`_mark_pending(uid, mail_uid, mail_meta, att)` 的参数形状（`subject`/`sender`/`date` + `index`/`filename`）在 Task 1/3/4/8 的测试里全部对齐；`public_config` 新增字段名（`auto_import`/`pending_count`/`last_run_at`/`last_success_at`/`last_error`）在 Task 2 定义后，Task 7（API 校验）、Task 9（前端）均使用同一套字段名，未出现改名不一致。
