"""calculate_change_rate 环比计算的表征测试(含收窄 except 后的容错分支)。"""
from services.analysis import calculate_change_rate


def test_normal_growth():
    assert calculate_change_rate(150, 100) == 50.0


def test_previous_zero_current_nonzero_returns_none():
    assert calculate_change_rate(100, 0) is None


def test_both_zero_returns_zero():
    assert calculate_change_rate(0, 0) == 0


def test_current_zero_returns_minus_100():
    assert calculate_change_rate(0, 100) == -100


def test_non_numeric_input_returns_none():
    # 收窄为 (TypeError, ValueError) 后,非数值入参仍安全返回 None
    assert calculate_change_rate('x', 100) is None
    assert calculate_change_rate(100, None) is None
