# 邮箱账单后台自动导入 —— 设计文档

- 日期：2026-07-01
- 状态：已确认，待实现
- 关联现状代码：[backend/services/mailbox.py](../../../backend/services/mailbox.py)、[backend/api/mail.py](../../../backend/api/mail.py)、[frontend/src/views/Settings.vue](../../../frontend/src/views/Settings.vue)

## 1. 背景

项目已经有一版"从邮箱取账单"的功能（commit `356c347`）：用户在设置页配置 IMAP 授权码后，需要**手动**点"拉取账单邮件"，再对列表里每封邮件的每个附件**手动**点"导入"（zip 密码也要手动填）。底层的账单邮件识别（关键词匹配）、附件下载、zip 解压（含 AES/ZipCrypto 加密包）、写入用户数据目录、复用解析/去重管线等能力都已具备且是纯函数式设计（`services/mailbox.py` 不依赖 Flask 请求上下文，`uid`/`session_dir` 都显式传参），只是缺一个"自动触发"的入口。

本次目标：把这套手动流程，在用户主动开启的前提下，变成后台定时自动运行，免去日常手动点击；同时正视自动化里天然存在的"人不在场"限制（支付宝加密包密码是每次导出随机生成的，机器拿不到）。

## 2. 目标与非目标

**目标**
- 用户在设置页为已配置好的邮箱开启"自动导入"开关后，后台每天自动检查一次新邮件，能自动解压/解析的账单附件自动导入，无需再手动点击。
- 需要密码才能解压的 zip（主要是支付宝加密包）不猜测、不重试，进入"待处理"状态，在设置页给出数量提示，用户方便时手动补齐密码完成导入——交互复用现有的邮件列表 + 导入面板，不新增页面。
- 后台任务本身要"看得见"：能看到上次自动同步时间、是否失败（比如 IMAP 授权码过期），不能悄悄坏掉却毫无痕迹。

**非目标（本次不做）**
- 不做微信/邮件推送通知（用户评估后认为账单统计场景推送意义不大，且有滞后性）。
- 不扩展银行 PDF 解析器覆盖范围（目前仅支持民生/农行/中国银行三家，新增银行需要真实样本 PDF，用户手头暂无样本，作为独立后续需求）。
- 不做"发件人 → 家庭成员"的自动映射规则；自动导入的账单统一归属邮箱配置所属的登录账号本人。
- 不做用户可调的扫描频率 UI；频率是运维级参数（环境变量），默认每天一次。

## 3. 功能设计

### 3.1 全局开关

- `_mail_config.json` 新增字段 `auto_import`（bool，默认 `false`）。用户必须显式打开才会有后台任务访问其邮箱——邮箱访问权限较敏感，符合项目"隐私优先、用户掌控"的定位。
- 设置页邮箱卡片新增一个开关控件，紧挨"测试连接"按钮。仅当已保存过完整配置（host/address/授权码）时可开启。

### 3.2 后台调度

- 引入 `APScheduler`（`BackgroundScheduler`），在 `app.py` 启动时注册一个周期任务，默认间隔 24 小时（环境变量 `MAIL_AUTO_IMPORT_INTERVAL_HOURS` 可覆盖，纯运维参数，不在前端暴露）。
- 用 `os.environ.get('WERKZEUG_RUN_MAIN')` 判断跳过 Flask debug 重载器的子进程重复注册；生产环境 `DEBUG=False`、单进程运行（`app.py` 里就是 `app.run()`，非 gunicorn 多 worker），不存在并发跑同一任务的问题，无需额外分布式锁。
- 任务体：`services/mailbox.py` 新增 `auto_import_all()`，遍历 `services/auth.list_users()` 拿到全部 `uid`，跳过没开启 `auto_import` 的用户，其余的调用同一用户级别的 `auto_import_one(uid)`。
- `auto_import_one(uid)` 内部复用现有 `fetch_bills(uid, days=N)`（`N` 取一个较宽松的窗口，比如 35 天，覆盖"半个月到一个月才传一次账单"的使用习惯，同时不必每天全量翻旧邮件）拿到候选账单邮件列表，对每封邮件的每个附件：
  - 非 zip，或未加密 zip → 直接调用 `import_attachment(uid, ..., session_dir=os.path.join(UPLOAD_FOLDER, uid))` 自动完成解析入库（`session_dir` 在这里直接拼路径，不能用 `get_session_dir()`——那个依赖 Flask session/`current_user`，后台线程没有请求上下文）。
  - 加密 zip 解压失败（密码错误/未提供）→ 不重试，记入待处理列表。

### 3.3 待处理队列与角标

- 新增用户级文件 `upload/<uid>/_mail_pending.json`：记录当前"需要密码才能完成导入"的邮件（`mail_uid`、`subject`、`sender`、`date`、需要密码的附件 `[{index, filename}]`）。
- 每次 `auto_import_one(uid)` 跑完后：
  - 新发现的加密 zip 写入/更新此文件；
  - 已经在 `_mail_imported.json` 里出现过对应文件的条目，从待处理里摘除（说明用户后来手动补了密码，已完成导入）。
- `GET /api/mail/config` 的返回体（`public_config()`）新增 `pending_count` 字段（`_mail_pending.json` 的条目数），设置页邮箱卡片据此显示数字角标，例如"3 封待导入"。不需要为了这个数字单独发起一次 IMAP 连接——角标只读本地文件，真正点进去看邮件列表/填密码时才照旧走现有的 `fetch_bills`/`import_attachment` 交互。
- 手动 `import_attachment` 导入成功后，同步清理该邮件在 `_mail_pending.json` 里的记录（不用等下一次定时任务才消失）。

### 3.4 健壮性与可见性

- `_mail_config.json` 同级新增 `_mail_auto_status.json`，记录 `{last_run_at, last_success_at, last_error}`。每次 `auto_import_one` 跑完（无论成功、部分失败还是整体异常，比如 IMAP 登录失败/授权码过期）都更新一次。
- `public_config()` 一并把这三个字段返回给前端，设置页在邮箱卡片上用一行小字展示"上次自动同步：2026-06-30 03:00"或"自动同步失败：登录失败，请确认授权码是否过期"，让用户不用凭空猜后台任务是不是还活着。
- 单个用户的自动导入异常（IMAP 连接失败等）只记录到该用户的 `_mail_auto_status.json` 并 `logger.exception`，不能让一个用户的失败中断 `auto_import_all()` 里其他用户的处理。

### 3.5 成员归属

- 自动导入不传 `member_id`（即 `None`），和现有手动流程里"不选成员"时的默认行为完全一致——现有 `services/members.py` 的默认成员机制已经保证未指定归属时算作"本人"，不需要新逻辑。

### 3.6 去重

完全复用现有两层去重，不新增机制：
- 邮件/附件级：`_mail_imported.json` 按 `mail_uid` 记录已导入文件，`auto_import_one` 沿用同一份记录，不会重复下载/重复标记待处理。
- 交易级：`services/data_loader.py` 里 `_data_signature` + `drop_duplicates(subset=..., keep='first')` 已经处理"同一笔交易被不同文件重复带入"的情况，自动导入产生的新文件走的是同一条数据加载路径，天然享受这层去重。

## 4. 涉及改动点

**后端**
- `backend/services/mailbox.py`：新增 `auto_import_all()`、`auto_import_one(uid)`，`save_config()`/`public_config()` 支持读写 `auto_import` 开关，新增 `_mail_pending.json` 与 `_mail_auto_status.json` 的读写辅助函数，`import_attachment()` 成功后清理对应 pending 记录。
- `backend/app.py`：注册 `APScheduler` `BackgroundScheduler`，启动时按 `WERKZEUG_RUN_MAIN` 规则避免重复注册，应用退出时 `scheduler.shutdown()`。
- `backend/api/mail.py`：`POST /api/mail/config` 支持 `auto_import` 字段；`public_config()` 透出的字段自然带上 `pending_count`/`last_run_at`/`last_success_at`/`last_error`，无需新增路由。
- `backend/config.py`：新增 `MAIL_AUTO_IMPORT_INTERVAL_HOURS`（环境变量，默认 24）。
- `backend/requirements.txt`：新增 `APScheduler`。

**前端**
- `frontend/src/views/Settings.vue`：邮箱卡片新增"自动导入"开关、待处理数量角标、上次同步状态文案；待处理邮件在现有邮件列表里优先展示/高亮。
- `frontend/src/api/`：对应 mail 相关请求补充 `auto_import` 字段的读写。

## 5. 边界情况

- 用户开启自动导入但从未成功测试过连接（授权码错/host 错）：跑起来直接登录失败，记入 `last_error`，下次照常重试，不会把开关自动关掉（避免用户以为开着其实早已停摆——错误状态本身就是提示）。
- 用户在自动任务运行期间修改/清空了授权码：下一轮任务读取到的是最新配置，旧的失败状态会在下次成功后自然被覆盖。
- 用户删除了邮箱配置（`auth_code` 清空）：`auto_import_one` 里 `_connect()` 已有的 `ValueError('邮箱未配置完整…')` 会被捕获记入 `last_error`，不会崩溃整个调度任务。
- 待处理列表无限增长：延用 `_mail_imported.json` 现有的"最近 500 条"截断策略，`_mail_pending.json` 也按同样上限截断（按邮件日期保留最新）。

## 6. 验收标准

- [ ] 邮箱未开启自动导入时，不会有任何后台任务访问该用户邮箱。
- [ ] 开启后，等待一个调度周期（或手动触发一次 `auto_import_one` 验证），无密码 zip / 银行 PDF / 未加密附件应自动出现在交易记录里，无需手动点击。
- [ ] 支付宝加密 zip 无法自动解压时，出现在设置页"待处理"角标里，数字与实际未导入邮件数一致。
- [ ] 手动为某封待处理邮件填密码导入成功后，角标数字立即减少（不用等下次调度）。
- [ ] 同一封邮件的同一个附件不会被自动任务重复导入；同一笔交易不会因为自动导入 + 之前手动导入过而在统计里翻倍。
- [ ] 故意填错授权码开启自动导入，运行一轮后设置页能看到"自动同步失败"提示及原因，而不是静默无提示。
- [ ] 一个用户的邮箱异常不影响其他用户的自动导入正常执行。
