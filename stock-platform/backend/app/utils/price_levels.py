"""
三策略点位计算——全项目唯一定义处。

此前 analysis_service 与 report_service 各自实现线性/非线性买点公式与
MACD 状态天数统计，仅靠人肉保持一致；任一侧调参另一侧必然悄悄落后。
本模块只放纯函数，不依赖服务与数据库，便于单测。
"""
from typing import Dict, List, Optional, Tuple

# 纪律参数（原两处实现的共同常量；改动需同步前端写死的提示文案）
STOP_PCT = 0.92               # 纪律止损：-8%
LINEAR_PROFIT_PCT = 1.15      # 线性止盈：+15%
NONLINEAR_PROFIT_PCT = 1.46   # 非线性止盈：+46%
RSI_OVERSOLD = 30.0           # 非线性策略超卖阈值


def linear_buy_point(current: float, ma20: float) -> float:
    """线性策略（斐波那契回撤）：价格在MA20上方时取回撤50%位，否则回退5%；上限为现价-5%"""
    if ma20 < current:
        buy = current - 0.5 * (current - ma20)
    else:
        buy = current * 0.95
    return min(buy, current * 0.95)


def nonlinear_buy_point(rsi: float, ma20: float, bb_lower: float) -> float:
    """非线性策略：RSI超卖(<30)看布林下轨，否则看20日均线"""
    return bb_lower if rsi < RSI_OVERSOLD else ma20


def levels_with_targets(current: float, buy: float, profit_pct: float) -> Dict:
    """由买点生成 {buy, stop, profit, distance}；distance=现价高出买点的百分比"""
    return {
        'buy': round(buy, 2),
        'stop': round(buy * STOP_PCT, 2),
        'profit': round(buy * profit_pct, 2),
        'distance': round((current - buy) / current * 100, 2) if current else 0.0,
    }


def macd_state_days(above: List[bool]) -> Tuple[Optional[bool], int]:
    """MACD金叉状态与已持续天数：从最新一根向前数同状态连续根数。
    above: bool列表（MACD>Signal），按时间升序；空列表返回 (None, 0)"""
    if not above:
        return None, 0
    is_golden = bool(above[-1])
    days = 0
    for v in reversed(above):
        if bool(v) == is_golden:
            days += 1
        else:
            break
    return is_golden, days


def discipline_stop(current: float) -> float:
    """MACD信号型策略的纪律止损（-8%）"""
    return round(current * STOP_PCT, 2)
