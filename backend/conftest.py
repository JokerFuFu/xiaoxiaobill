"""
pytest 根 conftest —— 本项目是扁平布局(没有把 backend 做成 package),
测试需要能 import services.mailbox / config 等模块,这里显式把 backend/ 加进 sys.path。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
