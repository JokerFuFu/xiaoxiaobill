"""
API 蓝图模块

包含所有 API 路由的蓝图定义：
- auth:      登录/登出/用户管理(管理员)
- members:   成员维度
- files:     文件上传与管理
- session:   会话/演示模式
- analysis:  数据分析
- ai:        AI 对话检索 / 智能识别账单 / 智能分析
- reconcile: 对账中心 + 资金性质口径规则
- networth:  资产负债(账户/余额快照/净资产)
"""
from flask import Blueprint
from .files import files_bp
from .session import session_bp
from .analysis import analysis_bp
from .auth import auth_bp
from .members import members_bp
from .ai import ai_bp
from .reconcile import reconcile_bp
from .networth import networth_bp
from .income import income_bp
from .mail import mail_bp
from .home import home_bp


def register_blueprints(app):
    """注册所有 API 蓝图到 Flask 应用"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(reconcile_bp)
    app.register_blueprint(networth_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(mail_bp)
    app.register_blueprint(home_bp)


__all__ = ['register_blueprints', 'files_bp', 'session_bp', 'analysis_bp',
           'auth_bp', 'members_bp', 'ai_bp', 'reconcile_bp', 'networth_bp',
           'income_bp', 'mail_bp', 'home_bp']
