"""支付宝 CSV 解析器契约测试。fixture 为脱敏构造样本(GBK 编码,仿支付宝导出格式)。

覆盖:来源标签、必备列、时间 dtype、方向取值,以及退款金额取负。
注:退款检测此前有缺陷(status_column 误取 columns[0]='交易时间' 使判定恒 False),
已在 Phase 1 修复为直接定位「交易状态」列,退款回归见 test_parse_alipay_refund_amount_is_negative。
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


def test_parse_alipay_refund_amount_is_negative():
    """样本含一条「退款成功」记录,应被标记退款且金额取负(此前 status_column 误取
    交易时间列导致检测失效,Phase 1 修复)。"""
    df = parse_alipay_csv(FIXTURE)
    refunds = df[df['是否退款']]
    assert len(refunds) >= 1
    assert (refunds['金额'] <= 0).all()
