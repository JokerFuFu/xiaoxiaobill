"""
银行账单 CSV 解析器（支付宝样式）
解析由银行 PDF 对账单转换、且已与支付宝/微信去重、已按 转入/转出 分类的 CSV。
与支付宝 CSV 同列结构，但来源标记为「银行」，收/支 含 收入/支出/转入/转出。
"""
import csv as _csv
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def is_bank_csv(filepath):
    """通过文件头判断是否为本工具产出的银行样式 CSV。"""
    try:
        with open(filepath, encoding='utf-8-sig') as f:
            head = f.read(400)
        return ('银行对账单转换' in head) or ('PDF转支付宝样式' in head) or ('PDF 对账单转换' in head)
    except Exception:
        return False


def parse_bank_csv(filepath):
    """解析银行样式 CSV → 与平台一致的 DataFrame schema，来源='银行'。"""
    with open(filepath, encoding='utf-8-sig') as f:
        lines = f.readlines()
    header_idx = next((i for i, l in enumerate(lines) if l.startswith('交易时间,')), None)
    if header_idx is None:
        raise ValueError('银行CSV未找到表头行')
    reader = _csv.reader(lines[header_idx:])
    header = next(reader)
    recs = []
    for row in reader:
        if not row or not row[0].strip():
            continue
        d = dict(zip(header, row))
        try:
            amt = float(d.get('金额', '') or 0)
        except ValueError:
            continue
        # 方向只由 收/支 表达;负金额视作冲正,标退款并取绝对值,防负数污染统计
        is_reversal = amt < 0
        if is_reversal:
            logger.warning(f"银行CSV出现负金额行(按冲正处理): {d.get('交易时间')} {d.get('商品说明')} {amt}")
        recs.append({
            '交易时间': d.get('交易时间', '').strip(),
            '交易分类': d.get('交易分类', '其他').strip() or '其他',
            '交易对方': d.get('交易对方', '').strip(),
            '商品说明': d.get('商品说明', '').strip(),
            '收/支': d.get('收/支', '').strip(),
            '金额': abs(amt),
            '收/付款方式': d.get('收/付款方式', '').strip(),
            '交易状态': d.get('交易状态', '交易成功').strip() or '交易成功',
            '来源': '银行',
            '是否退款': is_reversal,
        })
    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df['交易时间'] = pd.to_datetime(df['交易时间'])
    df['月份'] = df['交易时间'].dt.strftime('%Y-%m')
    df['日期'] = df['交易时间'].dt.strftime('%Y-%m-%d')
    logger.info(f"成功解析银行CSV {filepath}: {len(df)} 条")
    return df
