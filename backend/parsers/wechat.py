"""
微信账单解析器
"""
import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 微信部分退款状态形如「已退款(¥5.00)」/「已退款（￥5.00）」
_PARTIAL_REFUND_RE = re.compile(r'退款[（(]?[¥￥]\s*([\d,]+(?:\.\d+)?)')


def _mark_refunds(df):
    """退款打标(共用):
    - 部分退款(状态带退款金额且小于原金额):原行保留净额(金额-退款额),不打退款标——
      否则一笔 ¥30 只退 ¥5 的消费会被整行剔除,净消费 ¥25 凭空消失。
    - 全额退款/关闭/撤销:维持原口径(整行打标,金额取负,被统计剔除)。"""
    status = df['交易状态'].astype(str)
    refund_like = status.str.contains('退款|关闭|撤销', case=False, na=False)
    refund_amt = status.str.extract(_PARTIAL_REFUND_RE, expand=False).str.replace(',', '').astype(float)
    is_partial = refund_like & refund_amt.notna() & (refund_amt < df['金额'].abs() * 0.999)

    # 部分退款:净额化,不打退款标
    df.loc[is_partial, '金额'] = (df.loc[is_partial, '金额'].abs() - refund_amt[is_partial]).round(2)
    # 其余退款类:整行打标 + 负额(沿用全站口径)
    full_refund = refund_like & ~is_partial
    df['是否退款'] = full_refund
    df.loc[full_refund, '金额'] = -df.loc[full_refund, '金额'].abs()
    if is_partial.any():
        logger.info(f"微信部分退款净额化 {int(is_partial.sum())} 笔")
    return df


def parse_wechat_csv(filepath):
    """
    解析微信 CSV 账单文件

    Args:
        filepath: CSV 文件路径

    Returns:
        pandas.DataFrame: 解析后的数据框

    Raises:
        Exception: 解析失败时抛出异常
    """
    try:
        # 微信 CSV 处理逻辑
        with open(filepath, encoding='utf-8-sig') as f:
            lines = f.readlines()
            header_row = None
            for i, line in enumerate(lines):
                if '交易时间' in line and '交易类型' in line:
                    header_row = i
                    break

        if header_row is None:
            raise ValueError("无法找到微信账单表头行")

        df = pd.read_csv(filepath, encoding='utf-8-sig', skiprows=header_row)

        # 映射列名
        df = df.rename(columns={
            '交易类型': '交易分类',
            '商品': '商品说明',
            '金额(元)': '金额',
            '当前状态': '交易状态',
            '支付方式': '收/付款方式'
        })

        # 清理金额列 (移除 '¥')
        df['金额'] = df['金额'].astype(str).str.replace('¥', '').str.replace(',', '').astype(float)

        # 处理时间
        df['交易时间'] = pd.to_datetime(df['交易时间'])
        df['月份'] = df['交易时间'].dt.strftime('%Y-%m')
        df['日期'] = df['交易时间'].dt.strftime('%Y-%m-%d')

        # 标记退款(部分退款净额化)
        df = _mark_refunds(df)

        # 确保必要列
        if '交易对方' not in df.columns:
            df['交易对方'] = '未知'
        if '收/支' not in df.columns:
            df['收/支'] = '/'
        if '商品说明' not in df.columns:
            df['商品说明'] = ''

        df['来源'] = '微信'

        logger.info(f"成功解析微信 CSV 账单: {len(df)} 条记录")

        return df

    except Exception as e:
        logger.error(f"解析微信 CSV 失败: {str(e)}")
        raise


def parse_wechat_xlsx(filepath):
    """
    解析微信 XLSX 账单文件

    Args:
        filepath: XLSX 文件路径

    Returns:
        pandas.DataFrame: 解析后的数据框

    Raises:
        Exception: 解析失败时抛出异常
    """
    try:
        # 动态查找表头位置
        df_raw = pd.read_excel(filepath, header=None, engine='openpyxl')
        header_row = None

        # 查找包含关键列的行
        for i, row in df_raw.iterrows():
            row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
            if '交易时间' in row_str and ('交易类型' in row_str or '金额' in row_str):
                header_row = i
                break

        if header_row is None:
            raise ValueError("无法找到微信账单表头行，请确认文件格式正确")

        # 使用找到的表头行重新读取
        df = pd.read_excel(filepath, header=header_row, engine='openpyxl')

        # 检查是否是有效的微信账单（检查关键列）
        if '交易时间' not in df.columns:
            raise ValueError("不是有效的微信账单文件")

        # 映射列名以匹配支付宝格式
        # 处理不同的金额列名格式
        if '金额(元)' in df.columns and '金额' not in df.columns:
            df = df.rename(columns={'金额(元)': '金额'})

        df = df.rename(columns={
            '交易类型': '交易分类',
            '商品': '商品说明',
            '当前状态': '交易状态',
            '支付方式': '收/付款方式'
        })

        # 清理金额列 (移除 '¥' 和 ',')
        df['金额'] = df['金额'].astype(str).str.replace('¥', '').str.replace(',', '').astype(float)

        # 处理时间
        df['交易时间'] = pd.to_datetime(df['交易时间'])
        df['月份'] = df['交易时间'].dt.strftime('%Y-%m')
        df['日期'] = df['交易时间'].dt.strftime('%Y-%m-%d')

        # 标记退款(部分退款净额化)
        df = _mark_refunds(df)

        # 确保所有必要列都存在
        if '交易对方' not in df.columns:
            df['交易对方'] = '未知'
        if '收/支' not in df.columns:
            df['收/支'] = '/'
        if '商品说明' not in df.columns:
            df['商品说明'] = ''

        # 添加来源标识
        df['来源'] = '微信'

        logger.info(f"成功解析微信 XLSX 账单: {len(df)} 条记录")

        return df

    except Exception as e:
        logger.error(f"解析微信 XLSX 失败: {str(e)}")
        raise
