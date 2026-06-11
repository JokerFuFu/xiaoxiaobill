"""
Flask 应用主入口 - 蓝图重构版本

模块化架构:
- config.py: 配置常量
- utils/: 工具函数
- parsers/: 文件解析器
- services/: 业务逻辑
- api/: API 蓝图模块
"""
import os

from flask import Flask, jsonify, send_from_directory, abort
from flask_session import Session

# ============ 导入配置 ============
from config import (
    UPLOAD_FOLDER,
    SESSION_FILE_DIR,
    MAX_CONTENT_LENGTH,
    SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_TYPE,
    SESSION_FILE_THRESHOLD,
    SESSION_FILE_MODE,
    LOG_LEVEL,
    LOG_FILE,
    LOG_FORMAT,
    DEBUG,
    HOST,
    PORT,
)

# ============ 导入工具函数 ============
from utils.session import (
    get_session_dir,
    ensure_upload_dir,
)

# ============ 导入 API 蓝图 ============
from api import register_blueprints

# ============ 创建应用 ============
app = Flask(__name__)

# ============ 应用配置 ============
app.config.update(
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
    SESSION_TYPE=SESSION_TYPE,
    SESSION_FILE_DIR=SESSION_FILE_DIR,
    SESSION_FILE_THRESHOLD=SESSION_FILE_THRESHOLD,
    SESSION_FILE_MODE=SESSION_FILE_MODE,
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
)

# 密钥:优先环境变量;否则持久化到 data/.flask_secret(避免每次重启把所有人登出)
from secrets import token_hex
from config import SECRET_KEY_FILE


def _load_or_create_secret():
    env = os.environ.get('FLASK_SECRET_KEY')
    if env:
        return env
    try:
        if os.path.exists(SECRET_KEY_FILE):
            with open(SECRET_KEY_FILE) as f:
                s = f.read().strip()
                if s:
                    return s
        os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
        s = token_hex(32)
        with open(SECRET_KEY_FILE, 'w') as f:
            f.write(s)
        os.chmod(SECRET_KEY_FILE, 0o600)
        return s
    except Exception:
        return token_hex(32)


app.secret_key = _load_or_create_secret()

# ============ 初始化 Flask-Session ============
Session(app)

# ============ 初始化 Flask-Login(成熟鉴权方案) ============
from flask_login import LoginManager, current_user
from flask import request, session
from services.auth import get_user, ensure_admin

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def _load_user(uid):
    return get_user(uid)


@login_manager.unauthorized_handler
def _unauthorized():
    return jsonify({'success': False, 'error': '未登录', 'code': 'AUTH_REQUIRED'}), 401


# 公开(无需登录)的 API 前缀/路径
_PUBLIC_API = ('/api/auth/login', '/api/auth/logout', '/api/auth/me',
               '/api/session/status', '/api/demo/enter', '/api/demo/exit', '/api/ai/status')


@app.before_request
def _require_auth():
    """全局鉴权门:所有 /api/* 默认需要登录;演示模式可读;/api/admin/* 需管理员。"""
    p = request.path
    if not p.startswith('/api/'):
        return  # 前端静态/SPA 由 nginx/Flask 直接服务
    if p in _PUBLIC_API:
        return
    if session.get('is_demo'):
        # 演示模式:只读样本数据。正向白名单——禁止一切写操作与管理操作,
        # 仅放行 GET 以及少数只读/安全的 POST(进出演示、登出、AI 只读对话)。
        _demo_safe_post = ('/api/demo/enter', '/api/demo/exit', '/api/auth/logout', '/api/ai/chat')
        is_write = request.method != 'GET' and p not in _demo_safe_post
        if p.startswith('/api/admin/') or is_write:
            return jsonify({'success': False, 'error': '演示模式不可执行该操作'}), 403
        return
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': '未登录', 'code': 'AUTH_REQUIRED'}), 401
    if p.startswith('/api/admin/') and not current_user.is_admin:
        return jsonify({'success': False, 'error': '需要管理员权限'}), 403

# ============ 配置日志 ============
import logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ 注册 API 蓝图 ============
register_blueprints(app)
logger.info("API blueprints registered: files, session, analysis")

# ============ 注册新前端路由 ============
def register_new_frontend_routes():
    """注册新前端静态资源路由"""
    @app.route('/assets/<path:filename>')
    def serve_new_frontend_assets(filename):
        frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')
        assets_dir = os.path.join(frontend_dist, 'assets')
        if os.path.exists(os.path.join(assets_dir, filename)):
            return send_from_directory(assets_dir, filename)
        abort(404)

register_new_frontend_routes()

# ============ 启动时初始化 ============
ensure_upload_dir()
ensure_admin()  # 首次启动 bootstrap 管理员(uid=user_local,保留既有数据)

# ============ 前端路由 ============

@app.route('/')
@app.route('/index')
def index():
    """服务新前端"""
    frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    if os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, 'index.html')
    return jsonify({
        'error': '前端未构建，请先运行: cd frontend && npm run build'
    }), 503


@app.route('/yearly')
@app.route('/monthly')
@app.route('/category')
@app.route('/time')
@app.route('/transactions')
@app.route('/transfers')
@app.route('/channels')
@app.route('/insights')
@app.route('/analysis')
@app.route('/networth')
@app.route('/settings')
@app.route('/about-author')
@app.route('/login')
@app.route('/ai')
@app.route('/admin')
def serve_frontend_routes():
    """服务新前端 - SPA 路由支持"""
    frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    if os.path.exists(frontend_dist):
        return send_from_directory(frontend_dist, 'index.html')
    return jsonify({'error': '前端未构建'}), 503


@app.route('/favicon.ico')
def favicon():
    """处理 favicon 请求"""
    return '', 204


# ============ 错误处理 ============

@app.errorhandler(404)
def not_found_error(error):
    return "页面未找到 - 404", 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {str(error)}")
    return jsonify({
        'success': False,
        'error': '服务器内部错误，请稍后重试'
    }), 500


# ============ 启动代码 ============

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host=HOST, port=PORT, debug=DEBUG)
