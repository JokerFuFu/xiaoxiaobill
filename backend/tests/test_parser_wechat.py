"""微信 CSV 解析器契约测试。fixture 为脱敏构造样本(utf-8-sig,仿微信导出格式)。"""
import os

import pandas as pd

from parsers.wechat import parse_wechat_csv

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'wechat_sample.csv')


def test_parse_wechat_source_label():
    df = parse_wechat_csv(FIXTURE)
    assert (df['来源'] == '微信').all()


def test_parse_wechat_columns_and_dtype():
    df = parse_wechat_csv(FIXTURE)
    for col in ['交易时间', '金额', '收/支', '交易对方', '商品说明', '是否退款']:
        assert col in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df['交易时间'])


def test_parse_wechat_refund_amount_is_negative():
    df = parse_wechat_csv(FIXTURE)
    refunds = df[df['是否退款']]
    assert len(refunds) >= 1              # 样本含一条「已全额退款」
    assert (refunds['金额'] <= 0).all()   # 退款净额化为负
