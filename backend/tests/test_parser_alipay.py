"""支付宝 CSV 解析器契约测试。fixture 为脱敏构造样本(GBK 编码,仿支付宝导出格式)。

说明:退款金额取负逻辑存在已知缺陷(status_column 误取到 columns[0]='交易时间',
导致 df['交易状态'] 判定失效),该缺陷的修复 + 退款回归测试放在 Phase 1「修问题」。
本文件只锁定当前稳固的既有行为(来源标签、必备列、时间 dtype)。
"""
import os

import pandas as pd

from parsers.alipay import parse_alipay_csv

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'alipay_sample.csv')


def test_parse_alipay_source_label():
    df = parse_alipay_csv(FIXTURE)
    assert (df['来源'] == '支付宝').all()


def test_parse_alipay_columns_and_dtype():
    df = parse_alipay_csv(FIXTURE)
    for col in ['交易时间', '金额', '收/支', '交易对方', '商品说明', '交易分类', '是否退款']:
        assert col in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df['交易时间'])


def test_parse_alipay_direction_values_valid():
    df = parse_alipay_csv(FIXTURE)
    # 方向(收/支)取值应落在合法集合内
    assert set(df['收/支'].unique()) <= {'支出', '收入', '不计收支', '/'}
