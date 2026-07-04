"""数据分析 API 蓝图。

原单文件 api/analysis.py(1571 行)按域拆分为子模块(members/overview/yearly/monthly/
category/transactions/time_analysis),所有 /api 路由路径、端点名(analysis.<func>)、
蓝图名均保持不变,既有 API 向后兼容。
"""
import logging

from flask import Blueprint

from config import LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)

analysis_bp = Blueprint('analysis', __name__)

# 蓝图定义后再导入各域子模块,以触发 @analysis_bp.route 注册
from . import (  # noqa: E402,F401
    members, overview, yearly, monthly, category, transactions, time_analysis,
)
