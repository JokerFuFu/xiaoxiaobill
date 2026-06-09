"""
数据加载服务
"""
import pandas as pd
import logging
import os

from datetime import timedelta

from flask import session
from parsers.alipay import parse_alipay_csv
from parsers.wechat import parse_wechat_csv, parse_wechat_xlsx
from parsers.bank import parse_bank_pdf
from parsers.bank_csv import parse_bank_csv
from utils.file_utils import detect_file_source
from utils.session import get_session_dir

logger = logging.getLogger(__name__)


# 去重所用的稳定标识列(含「成员」:不同成员的同形态交易不应被合并)
_DEDUP_KEYS = ['交易时间', '金额', '来源', '交易对方', '商品说明', '收/支', '成员']

# 平台(支付宝/微信)转账类分类 → 统一归一为 转入/转出，与银行口径一致
_TRANSFER_CATS = ['转账', '转账红包', '群收款', '微信红包', '微信红包（群红包）', '微信红包（单发）', '二维码收款', '红包']


def _normalize_platform_transfers(df):
    """把平台转账/红包/群收款(原 收入/支出) 归一为 转入/转出；余额宝/理财类的 不计收支 保留为内部搬运。"""
    if '交易分类' not in df.columns:
        return df
    mask = df['来源'].isin(['支付宝', '微信']) & df['交易分类'].astype(str).isin(_TRANSFER_CATS)
    df.loc[mask & (df['收/支'] == '收入'), '收/支'] = '转入'
    df.loc[mask & (df['收/支'] == '支出'), '收/支'] = '转出'
    return df


# 跨源去重设计说明：
# 银行流水中『对手含支付宝/财付通』的快捷支付＝平台代扣，bank 解析器已统一标记为『不计收支/平台代扣』。
# - 2026 年：这些消费已在支付宝/微信账单(平台侧)统计一次，银行侧不计 → 不双算。
# - 2025 年：平台账单未导出，银行侧无法可靠还原商户/转账/退款，故同样不计；如需准确统计 2025 年消费，
#   请补传 2025 年的支付宝/微信账单(届时平台侧会正确计入，银行平台代扣仍不计，自动去重)。


def load_demo_data():
    """
    加载演示模式数据

    Returns:
        pandas.DataFrame: 演示数据
    """
    from config import DATA_DIR

    sample_file = os.path.join(DATA_DIR, 'sample_data.csv')
    if not os.path.exists(sample_file):
        raise FileNotFoundError("示例数据文件不存在")

    df = pd.read_csv(sample_file)
    df['交易时间'] = pd.to_datetime(df['交易时间'])
    df['月份'] = df['交易时间'].dt.strftime('%Y-%m')
    df['日期'] = df['交易时间'].dt.strftime('%Y-%m-%d')

    # 确保演示数据也有这些列
    if '是否退款' not in df.columns:
        df['是否退款'] = False
    if '来源' not in df.columns:
        df['来源'] = '示例数据'
    if '成员' not in df.columns:
        df['成员'] = '本人'

    logger.info(f"加载演示数据: {len(df)} 条记录")
    return df


def load_alipay_data():
    """
    加载并合并所有账单数据

    Returns:
        pandas.DataFrame: 合并后的数据框

    Raises:
        FileNotFoundError: 未找到任何账单文件
        Exception: 加载失败时抛出异常
    """
    try:
        # 演示模式逻辑
        if session.get('is_demo'):
            return load_demo_data()

        session_dir = get_session_dir()
        all_data = []

        # 成员维度:解析每个文件后,按 文件→成员 映射盖上「成员」列(整份文件归一个成员)
        from services.members import get_file_member_map, member_name_map, default_member_id
        uid = os.path.basename(session_dir)
        try:
            file_member = get_file_member_map(uid)
            name_map = member_name_map(uid)
            default_mid = default_member_id(uid)
        except Exception:
            file_member, name_map, default_mid = {}, {}, None

        def _member_of(fn):
            mid = file_member.get(fn, default_mid)
            return name_map.get(mid, '本人')

        # 读取会话目录中的所有文件
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            df = None

            # 处理 CSV 文件
            if filename.endswith('.csv'):
                try:
                    src = detect_file_source(filepath)
                    if src == 'wechat':
                        df = parse_wechat_csv(filepath)
                    elif src == 'bank-csv':
                        df = parse_bank_csv(filepath)   # 银行 PDF 转换的支付宝样式 CSV(已去重/已分类转入转出)
                    else:
                        df = parse_alipay_csv(filepath)
                except Exception as e:
                    logger.error(f"处理 CSV 文件 {filename} 失败: {str(e)}")
                    continue

            # 处理 XLSX 文件 (微信)
            elif filename.endswith('.xlsx'):
                try:
                    df = parse_wechat_xlsx(filepath)
                except Exception as e:
                    logger.error(f"处理 XLSX 文件 {filename} 失败: {str(e)}")
                    continue

            # 处理 PDF 文件 (银行账单)
            elif filename.lower().endswith('.pdf'):
                try:
                    df = parse_bank_pdf(filepath)
                except Exception as e:
                    logger.error(f"处理 PDF 银行账单 {filename} 失败: {str(e)}")
                    continue

            if df is not None and not df.empty:
                df['成员'] = _member_of(filename)   # 整份文件归属同一成员
                all_data.append(df)

        if not all_data:
            raise FileNotFoundError("未找到任何支付宝(.csv)/微信(.xlsx)/银行(.pdf)账单文件")

        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 交易级去重：修复重复上传/日期区间重叠导致的同笔重复统计
        before = len(combined_df)
        subset = [c for c in _DEDUP_KEYS if c in combined_df.columns]
        combined_df = combined_df.drop_duplicates(subset=subset, keep='first')
        if before != len(combined_df):
            logger.info(f"交易级去重: {before} → {len(combined_df)} (删 {before - len(combined_df)} 重复)")

        # 平台转账归一为 转入/转出（与银行口径一致，便于转账统计）
        combined_df = _normalize_platform_transfers(combined_df)

        # 清理内部辅助列
        for c in ['_bclass', '_platdup']:
            if c in combined_df.columns:
                combined_df = combined_df.drop(columns=[c])

        combined_df = combined_df.sort_values('交易时间')
        logger.info(f"加载账单数据: {len(combined_df)} 条记录")

        return combined_df

    except Exception as e:
        logger.error(f"加载数据失败: {str(e)}")
        raise


def clear_data_cache():
    """
    清除数据缓存

    Returns:
        bool: 清除成功返回 True
    """
    from utils.session import user_cache

    if 'user_id' in session:
        user_id = session['user_id']
        # 获取 load_alipay_data 函数的 clear_cache 方法
        if hasattr(load_alipay_data, 'clear_cache'):
            load_alipay_data.clear_cache(user_id)
        return True
    return False
