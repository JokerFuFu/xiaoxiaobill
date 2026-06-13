"""
应用配置常量
"""
import os
from datetime import timedelta

# ============ 目录配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'upload')
SESSION_FILE_DIR = os.path.join(DATA_DIR, 'flask_sessions')

# ============ 多用户/鉴权配置 ============
USERS_FILE = os.path.join(DATA_DIR, 'users.json')          # 全局账号表(werkzeug 哈希密码)
SECRET_KEY_FILE = os.path.join(DATA_DIR, '.flask_secret')  # 持久化 secret,避免重启登出
# 首次启动 bootstrap 管理员(uid 固定 user_local 以保留既有数据目录)
# 真实账号/口令通过环境变量(.env)注入;代码内仅留通用默认,避免 PII/口令入库
BOOTSTRAP_ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
BOOTSTRAP_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin12345')
BOOTSTRAP_ADMIN_DISPLAY = os.environ.get('ADMIN_DISPLAY', '管理员')
# 部署者是否沿用内置默认口令(没在 .env 里设 ADMIN_PASSWORD)。
# 仅在「为真 + 管理员从未改过密码」时,登录页才会展示默认账号方便首次进入——
# 此口令本就明文写在开源仓库里,改密后立即停止暴露,不泄露任何新信息。
BOOTSTRAP_USED_DEFAULT_PW = os.environ.get('ADMIN_PASSWORD', '') in ('', 'admin12345')

# ============ AI(Anthropic 兼容端点,默认 Kimi) ============
AI_BASE_URL = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.kimi.com/coding/').rstrip('/')
AI_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
AI_MODEL = os.environ.get('AI_MODEL', 'kimi-k2-0905-preview')
AI_ENABLED = bool(AI_API_KEY)

# ============ 文件上传配置 ============
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# ============ 会话配置 ============
# 本地部署不需要会话过期和自动清理

# ============ Flask Session 配置 ============
SESSION_COOKIE_SECURE = False  # 本地开发环境设为 False
SESSION_COOKIE_HTTPONLY = True  # 防止 JavaScript 访问 cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # 防止 CSRF 攻击
SESSION_TYPE = 'filesystem'
SESSION_FILE_THRESHOLD = 500  # 最大 Session 文件数
SESSION_FILE_MODE = 0o600  # 文件权限 (仅所有者可读写)

# ============ 日志配置 ============
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'app.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============ 应用配置 ============
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000  # Flask 默认端口，与 Docker 配置保持一致

# ============ 分类颜色映射 ============
CATEGORY_COLORS = {
    '餐饮美食': '#FF3B30',
    '酒店旅游': '#5856D6',
    '交通出行': '#007AFF',
    '购物消费': '#FF9500',
    '生活缴费': '#FFCC00',
    '通信服务': '#4CD964',
    '休闲娱乐': '#5AC8FA',
    '医疗健康': '#FF2D55',
    '教育培训': '#8E8E93',
    '理财投资': '#AF52DE',
    '工资薪金': '#34C759',
    '奖金补贴': '#30B0C7',
    '其他收入': '#FF9500',
    '其他支出': '#8E8E93',
}

# ============ 金额区间配置 ============
AMOUNT_RANGES = {
    'small': 100,    # 小额消费阈值
    'large': 1000,   # 大额消费阈值
    'nighttime_start': 22,  # 夜间消费开始时间
    'nighttime_end': 6,     # 夜间消费结束时间
}

# ============ 分析配置 ============
LATTE_FACTOR_THRESHOLD = 50  # 拿铁因子金额阈值
LATTE_FACTOR_COUNT = 10       # 拿铁因子最少次数

# 默认分页参数
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100
