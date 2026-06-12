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


def save_config(uid, host=None, port=None, address=None, auth_code=None):
    """auth_code: None=不改 / ''=清除 / 其他=替换。"""
    with _mail_lock:
        old = load_config(uid)
        new = {
            'host': str(host if host is not None else old.get('host', '')).strip()[:100],
            'port': int(port if port is not None else old.get('port', 993) or 993),
            'address': str(address if address is not None else old.get('address', '')).strip()[:100],
            'auth_code': ('' if auth_code == '' else
                          (str(auth_code).strip() if auth_code is not None else old.get('auth_code', ''))),
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
    return {
        'host': cfg.get('host', ''), 'port': cfg.get('port', 993),
        'address': cfg.get('address', ''),
        'has_auth': bool(cfg.get('auth_code')),
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
                    raise ValueError('压缩包密码错误或未提供(支付宝/微信的账单包需要填密码)')
                raise
            except Exception as e:
                if 'Bad password' in str(e) or 'password' in str(e).lower():
                    raise ValueError('压缩包密码错误或未提供(支付宝/微信的账单包需要填密码)')
                raise
            out.append((_safe_name(os.path.basename(name)), data))
    if not out:
        raise ValueError('压缩包里没有可导入的账单文件(csv/xlsx/pdf)')
    return out


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

    saved = []
    for fn, data in files:
        path, real_name = _unique_path(session_dir, fn)
        with open(path, 'wb') as f:
            f.write(data)
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
        rec = imported.setdefault(str(mail_uid), {'files': [], 'at': ''})
        rec['files'] = sorted(set(rec['files'] + saved))
        rec['at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        _save_imported(uid, imported)

    logger.info(f"邮箱导入 {len(saved)} 个账单文件: {saved}")
    return {'files': saved}
