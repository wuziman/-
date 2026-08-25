"""utils/price_levels.py 纯函数单测（点位公式唯一定义处的回归锚点）"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.price_levels import (
    discipline_stop,
    levels_with_targets,
    linear_buy_point,
    macd_state_days,
    nonlinear_buy_point,
)


class TestLinearBuyPoint:
    def test_above_ma20_takes_fibonacci_retracement(self):
        # 现价110、MA20=100 → 回撤50%位=105，但被-5%上限(104.5)截断
        assert linear_buy_point(110.0, 100.0) == 104.5

    def test_below_ma20_falls_back_5pct(self):
        assert linear_buy_point(100.0, 110.0) == 95.0

    def test_capped_at_5pct_below_current(self):
        # MA20仅略低于现价时，回撤位会高于-5%上限，应被压到上限
        assert linear_buy_point(100.0, 99.8) == 95.0


class TestNonlinearBuyPoint:
    def test_oversold_uses_bb_lower(self):
        assert nonlinear_buy_point(25.0, 100.0, 90.0) == 90.0

    def test_normal_uses_ma20(self):
        assert nonlinear_buy_point(50.0, 100.0, 90.0) == 100.0

    def test_threshold_is_exclusive_at_30(self):
        assert nonlinear_buy_point(30.0, 100.0, 90.0) == 100.0


class TestLevelsWithTargets:
    def test_targets_and_distance(self):
        lv = levels_with_targets(100.0, 95.0, 1.15)
        assert lv['buy'] == 95.0
        assert lv['stop'] == 87.4   # 95*0.92
        assert lv['profit'] == 109.25  # 95*1.15
        assert lv['distance'] == 5.0

    def test_zero_current_no_crash(self):
        assert levels_with_targets(0.0, 95.0, 1.15)['distance'] == 0.0


class TestMacdStateDays:
    def test_counts_consecutive_state_from_latest(self):
        # 最新为金叉，向前连续4根金叉后遇死叉
        assert macd_state_days([False, True, True, True, True]) == (True, 4)

    def test_death_cross_streak(self):
        assert macd_state_days([True, True, False, False]) == (False, 2)

    def test_empty_series(self):
        assert macd_state_days([]) == (None, 0)


def test_discipline_stop():
    assert discipline_stop(100.0) == 92.0
