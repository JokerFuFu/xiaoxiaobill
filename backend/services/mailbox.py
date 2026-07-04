"""
邮箱取账单服务 —— 从任意 IMAP 邮箱拉取账单附件并导入。

通用设计:
- 不绑定任何邮箱厂商:QQ/163/126/Gmail/Outlook/iCloud 预设 + 自定义 IMAP 服务器
- 登录用「授权码/应用专用密码」(各家 IMAP 标准做法),不是登录密码
- 识别账单邮件:主题/发件人含 账单/流水/支付宝/微信/银行 等关键词 + 带 csv/xlsx/pdf/zip 附件
- 导入:zip 自动解压(支持 ZipCrypto 与 AES,支付宝/微信的加密包可传密码),
  解出的 csv/xlsx/pdf 直接落到用户数据目录,沿用整套解析/去重/资金性质流水线

配置存 upload/<uid>/_mail_config.json(0600,授权码不回传前端);
已导入记录存 _mail_imported.json(按邮件 UID 去重提示)。
"""
import email
import email.header
import imaplib
import io
import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta

from config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)
_mail_lock = threading.RLock()


class PasswordRequired(ValueError):
    """附件需要密码才能打开(加密 zip / 加密 PDF)。
    继承 ValueError 以兼容现有 API 层的 except ValueError(仍返回 400);
    编排层(auto_import_one)据此把附件记入待处理队列,而非当作普通失败跳过。"""


PRESETS = [
    {'name': 'QQ 邮箱', 'host': 'imap.qq.com', 'port': 993,
     'help': '邮箱网页版 → 设置 → 账号 → 开启 IMAP/SMTP 服务 → 生成授权码'},
    {'name': '163 邮箱', 'host': 'imap.163.com', 'port': 993,
     'help': '设置 → POP3/SMTP/IMAP → 开启 IMAP → 获取授权码'},
    {'name': '126 邮箱', 'host': 'imap.126.com', 'port': 993,
     'help': '设置 → POP3/SMTP/IMAP → 开启 IMAP → 获取授权码'},
    {'name': 'Gmail', 'host': 'imap.gmail.com', 'port': 993,
     'help': 'Google 账号 → 安全性 → 两步验证 → 应用专用密码'},
    {'name': 'Outlook', 'host': 'outlook.office365.com', 'port': 993,
     'help': '账户安全 → 应用密码(需开启两步验证)'},
    {'name': 'iCloud', 'host': 'imap.mail.me.com', 'port': 993,
     'help': 'appleid.apple.com → 登录与安全 → App 专用密码'},
]

# 账单邮件特征(主题/发件人,宽匹配——宁多勿漏,反正用户逐封确认导入)
BILL_HINT = re.compile(r'账单|对账单|对帐单|流水|交易|明细|信用卡|银行|支付宝|alipay|微信|wechat|财付通|tenpay|bill|statement|e-?statement', re.I)
ALLOWED_ATT_EXTS = ('.csv', '.xlsx', '.pdf', '.zip')
IMPORT_EXTS = ('.csv', '.xlsx', '.pdf')
MAX_ATT_SIZE = 30 * 1024 * 1024
MAX_SCAN = 300       # 时间窗内最多扫描的邮件数(取最新)
MAX_RESULTS = 30     # 最多返回的账单邮件数


# ============ 配置 ============
def _cfg_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_mail_config.json')


def _imported_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_mail_imported.json')


def load_config(uid):
    try:
        p = _cfg_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        logger.exception("读取邮箱配置失败")
    return {}


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


def _load_imported(uid):
    try:
        p = _imported_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save_imported(uid, data):
    # 只保留最近 500 条记录
    if len(data) > 500:
        items = sorted(data.items(), key=lambda kv: kv[1].get('at', ''), reverse=True)
        data = dict(items[:500])
    p = _imported_file(uid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)


# ============ IMAP ============
def _decode_header(s):
    """RFC2047 头解码(主题/发件人/文件名),容忍 gb 系编码。"""
    if not s:
        return ''
    try:
        parts = email.header.decode_header(s)
        out = []
        for val, enc in parts:
            if isinstance(val, bytes):
                for e in (enc, 'utf-8', 'gb18030'):
                    if not e:
                        continue
                    try:
                        out.append(val.decode(e))
                        break
                    except Exception:
                        continue
                else:
                    out.append(val.decode('utf-8', 'replace'))
            else:
                out.append(val)
        return ''.join(out).strip()
    except Exception:
        return str(s)[:120]


def _connect(cfg):
    host, port = cfg.get('host'), int(cfg.get('port', 993))
    addr, code = cfg.get('address'), cfg.get('auth_code')
    if not host or not addr or not code:
        raise ValueError('邮箱未配置完整(服务器/邮箱地址/授权码)')
    M = imaplib.IMAP4_SSL(host, port, timeout=25)
    # 网易系要求 IMAP ID,否则报 Unsafe Login;其他服务商发了也无害
    try:
        M.xatom('ID', '("name" "xiaoyaobill" "version" "1.0" "vendor" "xiaoyaoprivatebill")')
    except Exception:
        pass
    try:
        M.login(addr, code)
    except imaplib.IMAP4.error as e:
        raise ValueError(f'登录失败:请确认已开启 IMAP 且使用授权码(非登录密码)。服务器返回: {str(e)[:80]}')
    return M


def test_config(uid):
    cfg = load_config(uid)
    M = _connect(cfg)
    try:
        typ, data = M.select('INBOX', readonly=True)
        if typ != 'OK':
            raise ValueError('无法打开收件箱')
        total = int(data[0]) if data and data[0] else 0
        return {'ok': True, 'message': f'连接成功,收件箱共 {total} 封邮件'}
    finally:
        try:
            M.logout()
        except Exception:
            pass


def _att_filename(part):
    fname = part.get_filename()
    if fname:
        return _decode_header(fname)
    return ''


def _iter_attachments(msg):
    """遍历附件 part,返回 [(index, filename, size_bytes, part)]。index 为附件序号(稳定)。"""
    out = []
    idx = 0
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        disp = str(part.get('Content-Disposition') or '')
        fname = _att_filename(part)
        if not fname and 'attachment' not in disp.lower():
            continue
        if not fname:
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in ALLOWED_ATT_EXTS:
            continue
        payload = part.get_payload(decode=True) or b''
        out.append((idx, fname, len(payload), part))
        idx += 1
    return out


def _fetch_msg(M, mail_uid):
    typ, data = M.uid('FETCH', mail_uid, '(BODY.PEEK[])')
    if typ != 'OK' or not data or not data[0]:
        raise ValueError('读取邮件失败')
    raw = b''
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2:
            raw = item[1]
            break
    return email.message_from_bytes(raw)


def fetch_bills(uid, days=90):
    """搜索时间窗内的账单邮件(带账单类附件),返回列表供前端逐封导入。"""
    cfg = load_config(uid)
    M = _connect(cfg)
    try:
        typ, _ = M.select('INBOX', readonly=True)
        if typ != 'OK':
            raise ValueError('无法打开收件箱')
        since = (datetime.now() - timedelta(days=max(1, min(int(days), 365)))).strftime('%d-%b-%Y')
        typ, data = M.uid('SEARCH', None, f'(SINCE {since})')
        if typ != 'OK':
            raise ValueError('邮件搜索失败')
        uids = (data[0] or b'').split()
        uids = uids[-MAX_SCAN:]
        if not uids:
            return []

        # 先批量拉头部,按关键词筛候选(省流量;真正解析只对候选做)
        headers = {}
        for i in range(0, len(uids), 50):
            chunk = uids[i:i + 50]
            typ, resp = M.uid('FETCH', b','.join(chunk),
                              '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
            if typ != 'OK':
                continue
            cur_uid = None
            for item in resp:
                if isinstance(item, tuple) and len(item) >= 2:
                    m = re.search(rb'UID (\d+)', item[0])
                    cur_uid = m.group(1) if m else None
                    if cur_uid:
                        headers[cur_uid] = item[1]

        candidates = []
        for u in reversed(uids):           # 新邮件优先
            hdr = headers.get(u)
            if hdr is None:
                continue
            hmsg = email.message_from_bytes(hdr)
            subject = _decode_header(hmsg.get('Subject', ''))
            sender = _decode_header(hmsg.get('From', ''))
            if BILL_HINT.search(subject + ' ' + sender):
                candidates.append((u, subject, sender, hmsg.get('Date', '')))
            if len(candidates) >= MAX_RESULTS:
                break

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
    finally:
        try:
            M.logout()
        except Exception:
            pass


# ============ 导入 ============
def _safe_name(name):
    name = os.path.basename(str(name))
    name = re.sub(r'[\\/\x00-\x1f<>:"|?*]', '', name).strip()
    return name[:120] or 'attachment'


def _unique_path(session_dir, fname):
    path = os.path.join(session_dir, fname)
    if not os.path.exists(path):
        return path, fname
    stem, ext = os.path.splitext(fname)
    fname2 = f"{stem}_{datetime.now():%H%M%S}{ext}"
    return os.path.join(session_dir, fname2), fname2


def _fix_zip_name(n, flag_bits):
    """zip 内中文文件名:无 UTF-8 标志位时按 cp437→gb18030 纠正(国内工具常见)。"""
    if flag_bits & 0x800:
        return n
    try:
        return n.encode('cp437').decode('gb18030')
    except Exception:
        return n


def _extract_zip(raw, password=None):
    """解 zip(支持 ZipCrypto/AES),返回 [(filename, bytes)](仅账单类扩展名)。"""
    import pyzipper
    out = []
    try:
        zf = pyzipper.AESZipFile(io.BytesIO(raw))
    except Exception:
        raise ValueError('压缩包损坏或不是有效的 zip 文件')
    with zf:
        if password:
            zf.setpassword(str(password).encode('utf-8'))
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = _fix_zip_name(info.filename, info.flag_bits)
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMPORT_EXTS:
                continue
            if info.file_size > MAX_ATT_SIZE:
                continue
            try:
                data = zf.read(info)
            except RuntimeError as e:
                if 'password' in str(e).lower() or 'Bad password' in str(e):
                    raise PasswordRequired('压缩包密码错误或未提供(支付宝/微信的账单包需要填密码)')
                raise
            except Exception as e:
                if 'Bad password' in str(e) or 'password' in str(e).lower():
                    raise PasswordRequired('压缩包密码错误或未提供(支付宝/微信的账单包需要填密码)')
                raise
            out.append((_safe_name(os.path.basename(name)), data))
    if not out:
        raise ValueError('压缩包里没有可导入的账单文件(csv/xlsx/pdf)')
    return out


def _decrypt_pdf_if_needed(raw, password=None):
    """PDF 若加密:优先空密码(未加密 或 仅所有者加密的空用户口令),否则用 password 解密;
    解密后去掉加密另存返回(pdfminer/pdfplumber 才能稳定读取)。未加密的 PDF 原样返回,
    不做多余重写;打不开则抛 PasswordRequired(交由上层记入待处理/提示补密码)。"""
    import pikepdf

    def _resave(pw):
        with pikepdf.open(io.BytesIO(raw), password=pw) as pdf:
            if not pdf.is_encrypted:
                return raw  # 无加密,原样返回
            out = io.BytesIO()
            pdf.save(out)  # 去加密另存
            return out.getvalue()

    try:
        return _resave('')  # 空密码:未加密 或 仅所有者加密
    except pikepdf.PasswordError:
        pass  # 确实加密,需要用户密码,走下面的分支
    except Exception:
        return raw  # pikepdf 打不开但非密码原因(不支持的结构等):原样交给后续 pdfplumber 尝试,不误伤
    if not password:
        raise PasswordRequired('PDF 已加密,需要打开密码')
    try:
        return _resave(str(password))
    except pikepdf.PasswordError:
        raise PasswordRequired('PDF 打开密码错误')


def import_attachment(uid, mail_uid, att_index, zip_password=None, member_id=None, session_dir=None):
    """下载某封邮件的某个附件并导入用户数据目录。返回 {files:[...]}。"""
    cfg = load_config(uid)
    M = _connect(cfg)
    try:
        typ, _ = M.select('INBOX', readonly=True)
        if typ != 'OK':
            raise ValueError('无法打开收件箱')
        msg = _fetch_msg(M, str(mail_uid).encode())
    finally:
        try:
            M.logout()
        except Exception:
            pass

    atts = _iter_attachments(msg)
    hit = next((a for a in atts if a[0] == int(att_index)), None)
    if hit is None:
        raise ValueError('附件不存在(邮件可能已变动,请重新拉取)')
    _, fname, size, part = hit
    if size > MAX_ATT_SIZE:
        raise ValueError(f'附件超过 {MAX_ATT_SIZE // 1024 // 1024}MB 上限')
    raw = part.get_payload(decode=True) or b''

    if fname.lower().endswith('.zip'):
        files = _extract_zip(raw, zip_password)
    else:
        files = [(_safe_name(fname), raw)]

    # 加密 PDF(部分银行邮件账单,如中国银行):无论来自 zip 还是直接附件,带打开密码的 PDF
    # 用同一密码字段尝试解密,打不开抛 PasswordRequired -> 自动导入据此记入待处理、手动可补密码。
    # 局限:只有一个密码输入,故"加密 zip(密码A) 里再套一个不同密码B 的加密 PDF"无法一次补齐
    # (会一直停在待处理);现实中支付宝/微信 zip 装的是 csv/xlsx、银行加密 PDF 是直接附件,不触发该组合。
    _dec = []
    for fn, data in files:
        if fn.lower().endswith('.pdf'):
            data = _decrypt_pdf_if_needed(data, zip_password)
        _dec.append((fn, data))
    files = _dec

    saved = []
    for fn, data in files:
        path, real_name = _unique_path(session_dir, fn)
        with open(path, 'wb') as f:
            f.write(data)
        try:
            # 账单含账号/姓名/流水,尤其是从加密 PDF 解密后落盘的明文,按项目 0600 敏感文件约定收紧权限
            os.chmod(path, 0o600)
        except Exception:
            pass
        saved.append(real_name)

    # 成员归属(整份文件归一个成员,与手工上传一致)
    if member_id:
        try:
            from services.members import set_file_member
            for fn in saved:
                set_file_member(uid, fn, member_id)
        except Exception:
            logger.exception("邮件导入设置成员归属失败")

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


# ============ 自动导入:编排逻辑 ============
AUTO_IMPORT_WINDOW_DAYS = 35  # 覆盖"半月到一个月才传一次账单"的使用习惯


def auto_import_one(uid, days=None):
    """对单个用户跑一轮自动导入。
    能自动解压/解析的附件(未加密银行 PDF、未加密 zip、csv/xlsx)直接导入;
    需要密码的附件(加密 zip / 加密 PDF,如支付宝随机密码、中国银行加密对账单)不猜密码,
    记入待处理队列,等用户在设置页手动补密码完成导入。
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
    failed = 0  # 非密码类失败(损坏/无可导入内容/异常)——用于把"部分失败"体现到同步状态

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
            except PasswordRequired:
                # 加密 zip 或加密 PDF:不猜密码,记入待处理队列,等用户手动补密码
                _mark_pending(uid, mail_uid, m, a)
                pending_new += 1
            except ValueError:
                failed += 1
                logger.warning(
                    f"自动导入跳过附件(非密码类失败): uid={uid} mail_uid={mail_uid} idx={idx}")
            except Exception:
                failed += 1
                logger.exception(f"自动导入附件异常: uid={uid} mail_uid={mail_uid} idx={idx}")

    # 部分失败也让用户可见:有任一附件失败则本轮标记非成功 + 摘要,而非一律 ok=True
    if failed:
        _save_auto_status(uid, ok=False, error=f"{failed} 个附件本轮导入失败(详见日志)")
    else:
        _save_auto_status(uid, ok=True)
    return {'imported': imported_count, 'pending': pending_new, 'error': None}


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


def should_start_mail_scheduler(debug, werkzeug_run_main):
    """决定当前进程是否应该启动后台定时任务。
    生产环境(debug=False)只有一个进程,直接启动;开发环境 Flask debug 模式下
    reloader 会额外起一个子进程,只在真正对外服务的子进程(WERKZEUG_RUN_MAIN=='true')里启动,
    避免同一台机器上跑出两份定时任务。"""
    return (not debug) or werkzeug_run_main == 'true'


def validate_auto_import_request(auto_import, final_host, final_address, final_auth):
    """校验"即将生效"的邮箱配置是否足够开启自动导入;合法返回 None,否则返回错误提示。"""
    if not auto_import:
        return None
    if not (final_host and final_address and final_auth):
        return '请先完整配置邮箱(服务器/地址/授权码)再开启自动导入'
    return None
