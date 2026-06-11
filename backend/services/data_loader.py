"""
数据加载服务
"""
import pandas as pd
import logging
import os
import threading

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

    # 演示数据同样需要 转账归一 + 资金性质(否则对账中心在演示态会缺列)
    try:
        df = _normalize_platform_transfers(df)
        from services.nature import apply_nature
        df = apply_nature(df, None)   # 演示态无用户自定义规则
    except Exception:
        logger.exception("演示数据资金性质标注失败")
        if '资金性质' not in df.columns:
            df['资金性质'] = '其他'

    logger.info(f"加载演示数据: {len(df)} 条记录")
    return df


_df_cache = {}
_df_cache_lock = threading.Lock()
# 影响派生列(成员/资金性质)的辅助文件,纳入缓存签名:改动即失效重建
_MEMBER_FILES = ('_members.json', '_file_members.json', '_nature_rules.json')


def _data_signature(session_dir):
    """数据文件 + 成员映射文件的 (名, mtime, 大小);任一变化即缓存失效。无数据则抛 FileNotFoundError。"""
    parts, has_data = [], False
    for fn in sorted(os.listdir(session_dir)):
        fp = os.path.join(session_dir, fn)
        if not os.path.isfile(fp):
            continue
        is_data = fn.endswith('.csv') or fn.endswith('.xlsx') or fn.lower().endswith('.pdf')
        if is_data:
            has_data = True
        if is_data or fn in _MEMBER_FILES:
            try:
                st = os.stat(fp)
                parts.append((fn, int(st.st_mtime_ns), st.st_size))
            except OSError:
                pass
    if not has_data:
        raise FileNotFoundError("未找到任何支付宝(.csv)/微信(.xlsx)/银行(.pdf)账单文件")
    return tuple(parts)


def load_alipay_data():
    """
    加载并合并所有账单数据。

    进程内按「文件签名(mtime+大小)」缓存:文件未变直接返回缓存副本(约毫秒级),
    避免每次请求都重新解析/合并/去重所有账单(原先每次 ~2-3s)。上传/删除/改成员归属
    都会改变签名而自动失效。

    Returns:
        pandas.DataFrame: 合并后的数据框
    Raises:
        FileNotFoundError: 未找到任何账单文件
    """
    if session.get('is_demo'):
        return load_demo_data()

    session_dir = get_session_dir()
    uid = os.path.basename(session_dir)
    sig = _data_signature(session_dir)   # 无数据会抛 FileNotFoundError

    with _df_cache_lock:
        hit = _df_cache.get(uid)
        if hit is not None and hit[0] == sig:
            return hit[1].copy()

    df = _build_alipay_data(session_dir, uid)
    with _df_cache_lock:
        _df_cache[uid] = (sig, df)
    return df.copy()


def current_data_signature():
    """当前用户数据的签名(供上层做结果缓存)。无数据/演示态返回 None。"""
    if session.get('is_demo'):
        return None
    try:
        return _data_signature(get_session_dir())
    except Exception:
        return None


def _build_alipay_data(session_dir, uid):
    """真正解析并合并所有账单(无缓存)。"""
    try:
        all_data = []

        # 成员维度:解析每个文件后,按 文件→成员 映射盖上「成员」列(整份文件归一个成员)
        from services.members import get_file_member_map, member_name_map, default_member_id
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

        # 资金性质标注(三表模型地基):分类映射+关键词+用户口径规则,纯增列不改既有数据
        try:
            from services.nature import apply_nature
            combined_df = apply_nature(combined_df, uid)
        except Exception:
            logger.exception("资金性质标注失败(不阻断数据加载)")
            if '资金性质' not in combined_df.columns:
                combined_df['资金性质'] = '其他'   # 兜底列,保证下游(对账中心)永不缺列

        logger.info(f"加载账单数据: {len(combined_df)} 条记录")

        return combined_df

    except Exception as e:
        logger.error(f"加载数据失败: {str(e)}")
        raise


def clear_data_cache():
    """
    显式清除当前用户的内存数据缓存。

    注:缓存本身按文件签名自动失效,上传/删除已会自动重建;此处用于强制清除(如换数据)。

    Returns:
        bool: 清除成功返回 True
    """
    try:
        uid = os.path.basename(get_session_dir())
        with _df_cache_lock:
            _df_cache.pop(uid, None)
    except Exception:
        pass
    return True
    return False
