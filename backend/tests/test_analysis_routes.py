"""api/analysis 拆分为子模块后的 URL 回归测试。

DoD:所有 /api 分析路由的「路径 + 端点名 + 方法」在拆分前后必须逐一不变
(既有 API 向后兼容)。用精确集合相等,增删改任一路由都会被捕获。
"""
from flask import Flask

from api.analysis import analysis_bp

EXPECTED = {
    ('/api/analysis', 'analysis.get_analysis', 'GET'),
    ('/api/available_dates', 'analysis.get_available_dates', 'GET'),
    ('/api/available_years', 'analysis.get_available_years', 'GET'),
    ('/api/categories', 'analysis.get_categories', 'GET'),
    ('/api/category_analysis', 'analysis.category_analysis', 'GET'),
    ('/api/category_available_dates', 'analysis.get_category_available_dates', 'GET'),
    ('/api/category_detail/<month>/<category>', 'analysis.category_detail', 'GET'),
    ('/api/category_expenses', 'analysis.category_expenses', 'GET'),
    ('/api/category_trend/<category>', 'analysis.category_trend', 'GET'),
    ('/api/channel_analysis', 'analysis.channel_analysis', 'GET'),
    ('/api/daily_data', 'analysis.daily_data', 'GET'),
    ('/api/filtered_monthly_analysis', 'analysis.filtered_monthly_analysis', 'GET'),
    ('/api/member_analysis', 'analysis.member_analysis', 'GET'),
    ('/api/monthly_analysis', 'analysis.monthly_analysis', 'GET'),
    ('/api/monthly_data', 'analysis.get_monthly_data', 'GET'),
    ('/api/overview_data', 'analysis.get_overview_data', 'GET'),
    ('/api/summary', 'analysis.summary', 'GET'),
    ('/api/time_analysis', 'analysis.time_analysis', 'GET'),
    ('/api/top_transactions', 'analysis.get_top_transactions', 'GET'),
    ('/api/transactions', 'analysis.get_transactions', 'GET'),
    ('/api/yearly_analysis', 'analysis.yearly_analysis', 'GET'),
    ('/api/yearly_data', 'analysis.yearly_data', 'GET'),
}


def _registered_rules():
    app = Flask(__name__)
    app.register_blueprint(analysis_bp)
    return {
        (r.rule, r.endpoint, ','.join(sorted(m for m in r.methods if m not in ('HEAD', 'OPTIONS'))))
        for r in app.url_map.iter_rules()
        if r.endpoint != 'static'
    }


def test_analysis_routes_unchanged():
    assert _registered_rules() == EXPECTED
