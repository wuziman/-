"""市场判定：全项目唯一定义处。

历史bug：`"A" if code.isdigit() or "." in code` 会把 BRK.B / BF.B 等
带点美股代码误判为A股，导致整条分析链失败。正确做法是先剥掉点后缀
再判断——纯数字为A股（兼容 600519.SH 后缀写法），否则为美股。
"""


def detect_market(stock_code: str) -> str:
    """按代码判定市场：'A'（沪深A股）或 'US'（美股）。"""
    base = stock_code.split(".")[0]
    return "A" if base.isdigit() else "US"
