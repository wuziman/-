"""
测试全局配置：在导入任何 app 模块之前把数据库指向临时目录，
避免测试读写生产 stock_platform.db（此前测试直接写生产K线缓存、改动调度开关）。
"""
import os
import tempfile
from pathlib import Path

_DB_DIR = Path(tempfile.mkdtemp(prefix="stock_platform_test_"))
os.environ["STOCK_PLATFORM_DB"] = str(_DB_DIR / "test.db")
