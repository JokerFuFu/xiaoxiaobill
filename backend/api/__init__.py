"""
API 蓝图模块

包含所有 API 路由的蓝图定义：
- auth:     登录/登出/用户管理(管理员)
- members:  成员维度
- files:    文件上传与管理
- session:  会话/演示模式
- analysis: 数据分析
- ai:       AI 对话检索 / 智能识别账单
"""
from flask import Blueprint
from .files import files_bp
from .session import session_bp
from .analysis import analysis_bp
from .auth import auth_bp
from .members import members_bp
from .ai import ai_bp


def register_blueprints(app):
    """注册所有 API 蓝图到 Flask 应用"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(ai_bp)


__all__ = ['register_blueprints', 'files_bp', 'session_bp', 'analysis_bp',
           'auth_bp', 'members_bp', 'ai_bp']
