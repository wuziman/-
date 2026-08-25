# -*- coding: utf-8 -*-
"""
detect_market 市场判定测试
回归背景：原逻辑 `"." in code` 把 BRK.B 等带点美股代码误判为A股，
导致走A股数据链后整条分析失败。
运行：cd backend && python -m pytest tests/test_detect_market.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.market import detect_market


@pytest.mark.parametrize("code,expected", [
    # A股：纯数字
    ("600519", "A"),
    ("000001", "A"),
    ("301413", "A"),
    # A股：带交易所后缀写法（原逻辑兼容的行为必须保留）
    ("600519.SH", "A"),
    ("000001.SZ", "A"),
    # 美股：普通代码
    ("AAPL", "US"),
    ("MU", "US"),
    # 美股：带点代码（回归重点——原逻辑误判为A股）
    ("BRK.B", "US"),
    ("BRK.A", "US"),
    ("BF.B", "US"),
    ("RDS.A", "US"),
])
def test_detect_market(code: str, expected: str):
    assert detect_market(code) == expected
