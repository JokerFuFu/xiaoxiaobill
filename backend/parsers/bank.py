"""
银行账单(PDF)解析器
支持：中国民生银行、中国农业银行、中国银行 的个人账户对账单/交易明细 PDF。
输出与支付宝/微信解析器一致的 DataFrame schema，并对每笔做智能分类：
  收/支 ∈ 支出/收入/不计收支；不计收支 用于 自转账/资金搬运/投资理财/信用还款/平台代扣，
  这样工具的消费/收入统计不会被资金搬运污染，但流水仍保留在交易明细与银行卡维度里。
"""
import os
import re
import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# 本人姓名：用于识别"本人账户之间的互转"(自转账 → 不计收支)。
# 出于隐私，不在代码内硬编码真实姓名；如需启用自转账识别，请通过环境变量配置：
#   export BANK_SELF_NAME="你的姓名"
SELF_NAME = os.environ.get('BANK_SELF_NAME', '')


# ---------- 三家银行 PDF 逐笔解析 ----------
def _num(s):
    if s is None:
        return None
    s = str(s).replace(',', '').replace(' ', '').strip()
    if s in ('', '--', '----------', '-------------------'):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _card_from_text(text, fallback='0000'):
    """从对账单首页文本中尽力提取卡号后 4 位（隐私：不硬编码真实卡号）。"""
    m = re.search(r'(?:卡号|账号|账户)[^\d]*(\d[\d\s]{2,})', str(text or ''))
    if m:
        digits = re.sub(r'\D', '', m.group(1))
        if len(digits) >= 4:
            return digits[-4:]
    return fallback


def _parse_minsheng(pdf, bank='中国民生银行', card=None):
    if not card:
        card = _card_from_text(pdf.pages[0].extract_text() if pdf.pages else '')
    out = []
    # 兼容两种民生对账单排版:①每行以日期开头;②每行以「卡 <卡号> 」前缀开头(卡号可能折行到下一行),
    #   且日期后带 现转标志/交易渠道/交易机构/对方户名 等尾列。前缀与尾列均设为可选,两种格式通吃。
    for pg in pdf.pages:
        for line in (pg.extract_text() or '').splitlines():
            m = re.match(
                r'^(?:卡\s+\d+\s+)?(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.+?)\s+'
                r'(-?[\d,]+\.\d{2})\s+([\d,]+\.\d{2})'
                r'(?:\s+(\S+))?(?:\s+(\S+))?(?:\s+(\S+))?(?:\s+(.+?))?\s*$', line)
            if not m:
                continue
            d, t, summ, amt, bal, cashflag, chan, org, party = m.groups()
            out.append(dict(bank=bank, card=card, dt=datetime.strptime(d + ' ' + t, '%Y/%m/%d %H:%M:%S'),
                            amount=_num(amt), summary=summ.strip(),
                            party=(party or '').split('/')[0].strip(), balance=_num(bal)))
    return out


def _parse_abc(pdf, bank='中国农业银行', card=None):
    if not card:
        card = _card_from_text(pdf.pages[0].extract_text() if pdf.pages else '')
    out = []
    for pg in pdf.pages:
        for line in (pg.extract_text() or '').splitlines():
            m = re.match(r'^(\d{8})\s+(?:(\d{6})\s+)?(.+?)\s+([+-][\d,]*\.\d{2})\s+([\d,]+\.\d{2})\s+(.*)$', line)
            if not m:
                continue
            d, t, summ, amt, bal, rest = m.groups()
            toks = rest.split()
            party = toks[0] if toks else ''
            dt = datetime.strptime(d + (t or '000000'), '%Y%m%d%H%M%S')
            out.append(dict(bank=bank, card=card, dt=dt, amount=_num(amt), summary=summ.strip(),
                            party='' if party in ('--', '') else party, balance=_num(bal)))
    return out


def _parse_boc(pdf):
    out = []
    head = pdf.pages[0].extract_text().splitlines()
    cardline = [l for l in head if '借记卡号' in l]
    cardno = re.search(r'借记卡号：\s*(\d+)', cardline[0]).group(1) if cardline else '0000'
    card = cardno[-4:]
    for pg in pdf.pages:
        t = pg.extract_table()
        if not t:
            continue
        for row in t:
            if not row or row[0] in (None, '记账日期'):
                continue
            cells = [(c or '') for c in row[:12]]
            d, tm, cur, amt, bal, name, chan, site, memo, pname, pcard, pbank = cells
            if not re.match(r'\d{4}-\d{2}-\d{2}', d):
                continue
            name = name.split('\n')[0].strip()
            pname = pname.split('\n')[0].strip()
            dt = datetime.strptime(d + ' ' + (tm or '00:00:00'), '%Y-%m-%d %H:%M:%S')
            out.append(dict(bank='中国银行', card=card, dt=dt, amount=_num(amt), summary=name,
                            party='' if pname.startswith('---') else pname, balance=_num(bal)))
    return out


def _detect_and_parse(pdf):
    text = pdf.pages[0].extract_text() or ''
    if '民生银行' in text:
        return _parse_minsheng(pdf)
    if '农业银行' in text:
        return _parse_abc(pdf)
    if '中国银行' in text:
        return _parse_boc(pdf)
    return []


# ---------- 智能分类：bclass + 映射到工具 schema ----------
FUND_SUMM = ['转存', '续存', '转出', '转支', '转入', '购汇', '结汇', '基金', '理财', 'CD', '证券', '证转', '申购', '赎回', '质押', '定活', '通知存款']
INCOME_SUMM = ['工资', '薪资', '奖金', '结息', '利息']
INFLOW_SUMM = ['转账收入', '退回', '退款', '报销']
HOUSING_SUMM = ['房租', '正常还款', '房贷还', '按揭']
FEE_SUMM = ['短信费', '年费', '手续费', '工本费', '账户管理费']


def _bclass(r):
    s = str(r['summary']); p = str(r['party']); full = s + p; amt = r['amount']
    if any(k in full for k in ['支付宝', '财付通']):
        return 'PLATDUP'
    if '信用卡还款' in full or ('还款' in full and '信用卡' in full) or '月付' in full:
        return 'CARDPAY'
    if '抖音' in full:
        return 'CONSUME'
    if SELF_NAME and p == SELF_NAME:
        return 'SELF'
    if any(k in full for k in ['网商银行', '余额宝', '零钱', '腾讯', '三快']):
        return 'SELF'
    if 'Ⅱ' in full or 'Ⅲ' in full or '类账户' in full or '现存' in s or '自助存款' in s or '续存' in s or '转存' in s:
        return 'SELF'
    if any(k in s for k in FUND_SUMM):
        return 'FUNDMOVE'
    if '税务' in full or '个人所得税' in full or '个税' in full:
        return 'TAX'
    if '保险' in full or '人寿' in full:
        return 'INSURE'
    if '公积' in full:
        return 'GONGJIJIN'
    if any(k in s for k in HOUSING_SUMM):
        return 'HOUSING'
    if s == '房贷' and amt and amt > 0:
        return 'INCOME'
    if any(k in s for k in INFLOW_SUMM):
        return 'INFLOW'
    if any(k in s for k in INCOME_SUMM):
        return 'INCOME'
    if any(k in s for k in FEE_SUMM):
        return 'FEE'
    if any(k in full for k in ['律师', '鉴定', '诊所', '医疗', '医学会', '案']):
        return 'SPECIAL'
    if any(k in s for k in ['跨行转账', '手机转账', '网上支付', '汇款', '小额普通', '跨行', '转账', '银联入账', '网银', '清算', '代收付', '代付']):
        return 'INFLOW' if (amt and amt > 0) else 'XFER'
    if any(k in s for k in ['无卡支付', '消费', '快捷支付', '银联消费', 'POS', '刷卡', '扫码', '缴费', '银联']):
        return 'CONSUME'
    return 'OTHER'


# bclass → (收/支, 交易分类)；不计收支 的项不计入消费/收入统计，仅保留在流水与银行卡维度
_MAP = {
    'CONSUME':  ('支出', '银行卡消费'),
    'HOUSING':  ('支出', '住房'),
    'TAX':      ('支出', '税费'),
    'INSURE':   ('支出', '保险'),
    'SPECIAL':  ('支出', '法律医疗'),
    'FEE':      ('支出', '金融手续费'),
    'INCOME':   ('收入', '工资收入'),
    'GONGJIJIN':('不计收支', '公积金'),
    'SELF':     ('不计收支', '资金转移'),
    'FUNDMOVE': ('不计收支', '理财投资'),
    'XFER':     ('不计收支', '对外转账'),
    'INFLOW':   ('不计收支', '资金往来'),
    'CARDPAY':  ('不计收支', '信用还款'),
    'PLATDUP':  ('不计收支', '平台代扣'),
    'OTHER':    ('不计收支', '其他'),
}


def parse_bank_pdf(filepath):
    """解析单个银行 PDF → 工具 schema DataFrame。
    带磁盘缓存(按源文件 mtime)：PDF 解析较慢，缓存后后续分析秒级返回。"""
    import os
    import pdfplumber
    cache = filepath + '.cache.pkl'
    try:
        if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(filepath):
            return pd.read_pickle(cache)
    except Exception:
        pass
    rows = []
    with pdfplumber.open(filepath) as pdf:
        recs = _detect_and_parse(pdf)
    for r in recs:
        if r['amount'] is None or r['dt'] is None:
            continue
        bclass = _bclass(r)
        zh_dir, cat = _MAP.get(bclass, ('不计收支', '其他'))
        if bclass == 'INCOME' and not any(k in str(r['summary']) for k in ['工资', '薪资', '奖金']):
            cat = '其他收入'
        rows.append({
            '交易时间': r['dt'],
            '交易分类': cat,
            '交易对方': r['party'] or r['summary'],
            '商品说明': r['summary'],
            '收/支': zh_dir,
            '金额': abs(r['amount']),
            '收/付款方式': f"{r['bank']}储蓄卡({r['card']})",
            '来源': '银行',
            '是否退款': False,
            '_bclass': bclass,
            '_platdup': bclass == 'PLATDUP',
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df['交易时间'] = pd.to_datetime(df['交易时间'])
    df['月份'] = df['交易时间'].dt.strftime('%Y-%m')
    df['日期'] = df['交易时间'].dt.strftime('%Y-%m-%d')
    try:
        df.to_pickle(cache)
    except Exception:
        pass
    logger.info(f"成功解析银行账单 {filepath}: {len(df)} 条")
    return df
