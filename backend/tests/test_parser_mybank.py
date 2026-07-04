"""网商银行/余利宝 xlsx 解析器契约测试。fixture 为脱敏构造 xlsx(网商账户收支)。

除通用契约外,额外锁定两条关键口径(该解析器的核心价值):
- 「快捷支付-支付宝」流出 → 不计收支(出资腿,真正消费在支付宝账单,防双算)。
- 「结息」正向金额 → 收入·投资收益(真实投资收益,别处看不到)。
"""
import os

import pandas as pd

from parsers.mybank import parse_mybank_xlsx, is_mybank_xlsx

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'mybank_sample.xlsx')


def test_is_mybank_xlsx_detects_title():
    assert is_mybank_xlsx(FIXTURE) is True


def test_parse_mybank_source_and_dtype():
    df = parse_mybank_xlsx(FIXTURE)
    assert (df['来源'] == '银行').all()
    assert pd.api.types.is_datetime64_any_dtype(df['交易时间'])


def test_parse_mybank_direction_values_valid():
    df = parse_mybank_xlsx(FIXTURE)
    assert set(df['收/支'].unique()) <= {'收入', '支出', '转入', '转出', '不计收支'}


def test_parse_mybank_platform_payment_not_counted():
    """支付宝快捷支付出资腿不计收支,避免与支付宝流水重复计消费。"""
    df = parse_mybank_xlsx(FIXTURE)
    row = df[df['交易对方'] == '测试商户Z'].iloc[0]
    assert row['收/支'] == '不计收支'


def test_parse_mybank_interest_is_income():
    """结息 → 收入·投资收益。"""
    df = parse_mybank_xlsx(FIXTURE)
    income = df[df['交易分类'] == '投资收益']
    assert len(income) >= 1
    assert (income['收/支'] == '收入').all()
