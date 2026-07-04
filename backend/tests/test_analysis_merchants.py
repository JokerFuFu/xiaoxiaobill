"""services.analysis.analyze_merchants 的回归测试(纯 DataFrame,无文件 fixture)。"""
import pandas as pd

from services.analysis import analyze_merchants


def _sample_df():
    return pd.DataFrame({
        '交易时间': pd.to_datetime(
            ['2024-01-01 12:00', '2024-01-10 12:00', '2024-01-05 08:00']
        ),
        '收/支': ['支出', '支出', '收入'],
        '交易对方': ['商户A', '商户A', '老板'],
        '金额': [30.0, 20.0, 5000.0],
        '交易分类': ['餐饮', '餐饮', '工资'],
    })


def test_analyze_merchants_excludes_income():
    result = analyze_merchants(_sample_df())
    names = [m['name'] for m in result['frequent_merchants']]
    assert '老板' not in names  # 收入不计入商家消费


def test_analyze_merchants_aggregates_expense():
    result = analyze_merchants(_sample_df())
    a = next(m for m in result['frequent_merchants'] if m['name'] == '商户A')
    assert a['amount'] == 50.0     # 30 + 20
    assert a['count'] == 2
    assert a['last_visit'] == '2024-01-10'  # 最近一次
