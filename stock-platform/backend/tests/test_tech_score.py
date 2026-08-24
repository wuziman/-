# -*- coding: utf-8 -*-
"""
技术面评分共享函数测试：分支覆盖 + 与 analysis_service 一致性（防再漂移）
全部合成数据，不依赖网络。
运行：cd backend && python -m pytest tests/test_tech_score.py -v
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.tech_score import calculate_tech_score


def make_series(**overrides) -> pd.Series:
    """中性基线：RSI=50、价格贴着均线、布林带内——各分支均不触发。
    MACD默认NaN：规则里MACD<=信号线一律按死叉-1（含相等），无真正中性态，故跳过该分支"""
    base = {
        'Close': 100.0,
        'RSI': 50.0,
        'MACD': float('nan'),
        'MACD_Signal': float('nan'),
        'MA20': 100.0,
        'MA50': 100.0,
        'BB_Upper': 110.0,
        'BB_Lower': 90.0,
    }
    base.update(overrides)
    return pd.Series(base)


class TestBranchCoverage:
    def test_neutral_baseline_is_five(self):
        score, details = calculate_tech_score(make_series())
        assert score == 5.0
        assert details['current_price'] == 100.0

    # --- RSI 四个分支 ---
    def test_rsi_oversold_adds_two(self):
        score, d = calculate_tech_score(make_series(RSI=25.0))
        assert score == 7.0
        assert d['rsi'] == 25.0

    def test_rsi_below_forty_adds_one(self):
        assert calculate_tech_score(make_series(RSI=35.0))[0] == 6.0

    def test_rsi_overbought_subtracts_two(self):
        assert calculate_tech_score(make_series(RSI=75.0))[0] == 3.0

    def test_rsi_above_sixty_subtracts_one(self):
        assert calculate_tech_score(make_series(RSI=65.0))[0] == 4.0

    def test_rsi_nan_is_skipped(self):
        s = make_series()
        s.loc['RSI'] = float('nan')
        score, d = calculate_tech_score(s)
        assert score == 5.0
        assert 'rsi' not in d

    # --- MACD ---
    def test_macd_golden_adds_one(self):
        assert calculate_tech_score(make_series(MACD=1.0, MACD_Signal=0.5))[0] == 6.0

    def test_macd_death_subtracts_one(self):
        assert calculate_tech_score(make_series(MACD=-1.0, MACD_Signal=0.5))[0] == 4.0

    # --- 均线结构：站上+0.5 / 跌破-0.5 / 多头+0.5 / 空头-0.5（对称）---
    def test_full_bullish_ma_structure_adds_one_point_five(self):
        score, _ = calculate_tech_score(
            make_series(Close=105.0, MA20=100.0, MA50=98.0))
        assert score == 6.5

    def test_bearish_ma_structure_deducts_one_point_five(self):
        # 价格低于两条均线且空头排列、MACD死叉 → 死叉-1、均线三项-1.5
        score, _ = calculate_tech_score(
            make_series(Close=95.0, MA20=98.0, MA50=100.0,
                        MACD=-1.0, MACD_Signal=0.0))
        assert score == 2.5

    # --- 趋势前提：空头排列下超卖加分不启用（防接刀）---
    def test_oversold_bonus_disabled_in_bearish_alignment(self):
        """同结构下对照：多头排列 RSI=25 比 RSI=45 恰好多2分；
        空头排列两者同分（超卖加分被跳过）——均线结构保持一致以隔离变量"""
        def score(ma20, rsi):
            return calculate_tech_score(
                make_series(Close=90.0, RSI=rsi, MA20=ma20, MA50=95.0))[0]
        assert score(96.0, 25.0) == score(96.0, 45.0) + 2.0   # 多头排列：加分生效
        assert score(92.0, 25.0) == score(92.0, 45.0)          # 空头排列：不加分

    def test_bb_lower_break_disabled_in_bearish_alignment(self):
        """破下轨加分同样受趋势前提约束：空头排列破与不破同分；多头排列恰好多1分"""
        bear_break  = make_series(Close=89.0, MA20=92.0, MA50=95.0)   # 89<90 破下轨
        bear_within = make_series(Close=91.0, MA20=92.0, MA50=95.0)
        assert calculate_tech_score(bear_break)[0] == calculate_tech_score(bear_within)[0]
        bull_break  = make_series(Close=89.0, MA20=96.0, MA50=95.0)
        bull_within = make_series(Close=94.0, MA20=96.0, MA50=95.0)
        assert calculate_tech_score(bull_break)[0] == calculate_tech_score(bull_within)[0] + 1.0

    def test_crashing_stock_scores_low_not_buy(self):
        """回归：连续暴跌股（旧版实测得7分被判买入）现在必须落入谨慎区间"""
        crashing = make_series(
            Close=8.0, RSI=18.0,
            MACD=-0.5, MACD_Signal=-0.2,
            MA20=12.0, MA50=15.0,
            BB_Upper=11.0, BB_Lower=9.5,
        )
        # 5 -1(死叉) -1.5(跌破双均线+空头排列) ；超卖加分因空头排列不启用
        score, _ = calculate_tech_score(crashing)
        assert score == 2.5
        assert score < 3.5  # 推荐映射中「谨慎/观望」以下，绝不触发「买入」

    # --- 布林带 ---
    def test_below_bb_lower_adds_one(self):
        # Close=89：跌破双均线(-1.0)、贴线中性、破下轨(+1.0)，MACD分支NaN跳过
        assert calculate_tech_score(make_series(Close=89.0))[0] == 5.0

    def test_above_bb_upper_subtracts_one(self):
        # Close=111同时站上两条均线(+1.0)、破上轨(-1.0)，MACD分支为NaN跳过
        assert calculate_tech_score(make_series(Close=111.0))[0] == 5.0

    # --- 极值与钳位 ---
    def test_max_clamped_at_ten(self):
        bullish = make_series(RSI=25.0, MACD=1.0, MACD_Signal=0.0,
                              Close=101.0, MA20=100.0, MA50=99.0,
                              BB_Upper=110.0, BB_Lower=102.0)
        # 5 +2(RSI) +1(金叉) +1.5(均线) +1(破下轨) = 10.5 → 钳到10
        assert calculate_tech_score(bullish)[0] == 10.0

    def test_minimum_possible_score_clamped_at_zero(self):
        bearish = make_series(RSI=75.0, MACD=-1.0, MACD_Signal=0.0,
                              Close=111.0, MA20=112.0, MA50=115.0,
                              BB_Upper=110.0, BB_Lower=90.0)
        # 对称规则下：超买-2、死叉-1、跌破双均线+空头排列-1.5、破上轨-1 → -0.5 钳到0
        assert calculate_tech_score(bearish)[0] == 0.0


class TestConsistencyWithAnalysisService:
    def test_analyze_technical_delegates_to_shared_fn(self):
        """AnalysisService._analyze_technical 必须与共享函数逐位一致（防两份实现再漂移）"""
        from app.services.analysis_service import AnalysisService
        svc = AnalysisService()
        cases = [
            {},
            {'RSI': 25.0},
            {'RSI': 75.0},
            {'MACD': -2.0, 'MACD_Signal': 0.0},
            {'Close': 105.0, 'MA20': 100.0, 'MA50': 98.0},
            {'Close': 89.0},
        ]
        df = pd.DataFrame({'Close': [100.0]})
        for overrides in cases:
            latest = make_series(**overrides)
            shared_score, shared_details = calculate_tech_score(latest)
            svc_score, svc_details = svc._analyze_technical(df, latest)
            assert (svc_score, svc_details) == (shared_score, shared_details), \
                f"实现漂移！overrides={overrides}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
