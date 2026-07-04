"""api/analysis 拆分后的端点级冒烟测试。

用演示模式(session is_demo=True → 过鉴权门 + load_alipay_data 返回样本数据)真正
执行每个分析路由的函数体,断言不出 500。目的:兜住"拆分把某函数用到的名字留在了
别的子模块"这类跨模块 NameError(仅注册/导入测试无法发现)。
"""
import pytest

from app import app as flask_app

# 无路径参数的 GET 分析端点(逐一执行函数体)
PARAMLESS_ROUTES = [
    '/api/analysis',
    '/api/summary',
    '/api/overview_data',
    '/api/yearly_analysis',
    '/api/yearly_data',
    '/api/monthly_analysis',
    '/api/monthly_data',
    '/api/filtered_monthly_analysis',
    '/api/category_analysis',
    '/api/category_expenses',
    '/api/categories',
    '/api/category_available_dates',
    '/api/transactions',
    '/api/top_transactions',
    '/api/channel_analysis',
    '/api/member_analysis',
    '/api/time_analysis',
    '/api/daily_data',
    '/api/available_dates',
    '/api/available_years',
]

# 带路径参数的端点(给定合理参数,同样只断言不 500)
PARAM_ROUTES = [
    '/api/category_trend/餐饮美食',
    '/api/category_detail/2024-01/餐饮美食',
]


@pytest.fixture
def demo_client():
    flask_app.config['TESTING'] = True
    client = flask_app.test_client()
    with client.session_transaction() as sess:
        sess['is_demo'] = True
    return client


@pytest.mark.parametrize('route', PARAMLESS_ROUTES + PARAM_ROUTES)
def test_analysis_endpoint_no_server_error(demo_client, route):
    resp = demo_client.get(route)
    assert resp.status_code != 500, \
        f'{route} 返回 500(可能跨模块 NameError):{resp.get_data(as_text=True)[:300]}'
