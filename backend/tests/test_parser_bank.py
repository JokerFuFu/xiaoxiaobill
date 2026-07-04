"""银行样式 CSV 解析器契约测试(bank_csv 文本路径,避开重型 PDF fixture)。

样本为脱敏构造的「银行对账单转换」CSV,覆盖:来源标记、方向取值、
以及负金额冲正行 → 是否退款为真且金额取绝对值(防负数污染统计)。
"""
import os

import pandas as pd

from parsers.bank_csv import parse_bank_csv, is_bank_csv

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'bank_sample.csv')


def test_is_bank_csv_detects_marker():
    assert is_bank_csv(FIXTURE) is True


def test_parse_bank_csv_source_and_dtype():
    df = parse_bank_csv(FIXTURE)
    assert (df['来源'] == '银行').all()
    assert pd.api.types.is_datetime64_any_dtype(df['交易时间'])


def test_parse_bank_csv_direction_values_valid():
    df = parse_bank_csv(FIXTURE)
    assert set(df['收/支'].unique()) <= {'收入', '支出', '转入', '转出'}


def test_parse_bank_csv_reversal_is_abs_and_flagged():
    df = parse_bank_csv(FIXTURE)
    reversal = df[df['是否退款']]
    assert len(reversal) >= 1            # 样本含一条 -30.00 冲正
    assert (reversal['金额'] > 0).all()  # 取绝对值,不留负数
