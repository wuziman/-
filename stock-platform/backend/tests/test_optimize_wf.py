# -*- coding: utf-8 -*-
"""
第三批·回测优化测试：策略参数化 / 网格寻优(optimize) / Walk-Forward验证
全部使用合成数据直接调用服务方法，不依赖网络。
运行：cd backend && python -m pytest tests/test_optimize_wf.py -v
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.backtest_service import (
    BacktestService,
    PARAM_GRIDS,
    DEFAULT_PARAMS,
    METRIC_FIELDS,
)
from app.utils.indicators import calculate_all_indicators


# ============================================
# 合成数据（与改造前基准采集所用完全一致：seed=7 波动上行260日）
# ============================================
def make_wave_df(days: int = 260, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(days)
    close = np.round(100 + 20 * np.sin(t / 15) + 0.08 * t + rng.normal(0, 0.4, days), 2)
    open_ = np.round(close + rng.normal(0, 0.3, days), 2)
    high = np.round(np.maximum(open_, close) + 0.8, 2)
    low = np.round(np.minimum(open_, close) - 0.8, 2)
    idx = pd.date_range('2025-01-01', periods=days, freq='B')
    return pd.DataFrame({'Open': open_, 'High': high, 'Low': low,
                         'Close': close, 'Volume': 1_000_000}, index=idx)


def _wave_with_indicators(days: int = 260, seed: int = 7) -> pd.DataFrame:
    return calculate_all_indicators(make_wave_df(days, seed))


# 当前引擎在同一合成数据上的结果（回归锚点）
# 2026-08-23 重锚：修复前视偏差(ma_cross/macd金叉按收盘价成交)与止盈止损改为盘中High/Low路径判定，
# 旧锚点(97584.93/106926.12/108746.52/206779.52)对应的是带bug的旧行为
BASELINE = {
    # strategy: (final_value, len(trades))
    'linear': (97236.78, 6),
    'nonlinear': (101119.17, 13),
    'ma_cross': (108621.99, 4),
    'macd': (206913.31, 5),
}


# ============================================
# 策略参数化：不传参数 = 原硬编码结果；显式默认参数 = 不传参数
# ============================================
class TestParametrizedStrategies:
    def test_default_matches_pre_refactor_baseline(self):
        """4策略不传params必须与旧硬编码逻辑逐位一致（final_value/成交笔数）"""
        svc = BacktestService()
        dfi = _wave_with_indicators()
        for strat, (exp_final, exp_trades) in BASELINE.items():
            fn = getattr(svc, f'_backtest_{strat}')
            trades, curve = fn(dfi, 100000, 1.0)
            assert curve[-1][1] == exp_final, \
                f"{strat} 默认参数回归失败: {curve[-1][1]} != {exp_final}"
            assert len(trades) == exp_trades

    @pytest.mark.parametrize('strategy', ['linear', 'nonlinear', 'ma_cross', 'macd'])
    def test_explicit_default_params_equal_no_params(self, strategy):
        """显式传入默认参数dict的结果与不传参数完全一致"""
        svc = BacktestService()
        dfi = _wave_with_indicators()
        fn = getattr(svc, f'_backtest_{strategy}')
        tr_none, c_none = fn(dfi.copy(), 100000, 1.0)
        tr_def, c_def = fn(dfi.copy(), 100000, 1.0, dict(DEFAULT_PARAMS[strategy]))
        assert c_none == c_def and tr_none == tr_def

    def test_linear_tp_sl_params_change_behavior(self):
        """自定义tp/sl生效：放宽止盈止损后交易行为应改变且曲线仍完整"""
        svc = BacktestService()
        dfi = _wave_with_indicators()
        _, c_tight = svc._backtest_linear(dfi.copy(), 100000, 1.0,
                                          {'tp': 0.05, 'sl': 0.03})
        _, c_loose = svc._backtest_linear(dfi.copy(), 100000, 1.0,
                                          {'tp': 0.30, 'sl': 0.20})
        assert c_tight[-1][1] != c_loose[-1][1]
        assert len(c_tight) == len(c_loose) == len(dfi) - 50
        # sl允许负数写法（取绝对值），与正数幅度等价
        _, c_neg = svc._backtest_linear(dfi.copy(), 100000, 1.0,
                                        {'tp': 0.05, 'sl': -0.03})
        assert c_neg[-1][1] == c_tight[-1][1]

    def test_ma_cross_custom_params_no_df_pollution(self):
        """非默认fast/slow在副本上现算均线，不得污染调用方DataFrame的MA20/MA50列"""
        svc = BacktestService()
        dfi = _wave_with_indicators()
        ma20_before = dfi['MA20'].copy()
        ma50_before = dfi['MA50'].copy()
        trades, curve = svc._backtest_ma_cross(dfi, 100000, 1.0, {'fast': 10, 'slow': 40})
        assert dfi['MA20'].equals(ma20_before)
        assert dfi['MA50'].equals(ma50_before)
        assert len(curve) == len(dfi) - 50  # 循环仍从第50根开始

    def test_macd_custom_params_recompute(self):
        """非默认fast/slow/signal内部现算EMA差与信号线，曲线长度不变且结果可复现"""
        svc = BacktestService()
        dfi = _wave_with_indicators()
        params = {'fast': 8, 'slow': 21, 'signal': 7}
        tr1, c1 = svc._backtest_macd(dfi.copy(), 100000, 1.0, dict(params))
        tr2, c2 = svc._backtest_macd(dfi.copy(), 100000, 1.0, dict(params))
        assert c1 == c2 and len(c1) == len(dfi) - 50
        # 与默认参数结果区分开（参数确实参与计算）
        _, c_default = svc._backtest_macd(dfi.copy(), 100000, 1.0)
        assert not (c1[-1][1] == c_default[-1][1] and tr1 == _)

    def test_start_override_for_walk_forward(self):
        """start=1时权益曲线覆盖除首根外的全部bar（walk-forward测试段用）"""
        svc = BacktestService()
        dfi = _wave_with_indicators()
        trades, curve = svc._backtest_linear(dfi, 100000, 1.0, start=1)
        assert len(curve) == len(dfi) - 1


# ============================================
# optimize 网格寻优
# ============================================
class TestOptimize:
    def _svc_with_mock(self, monkeypatch, days: int = 300) -> BacktestService:
        svc = BacktestService()
        df = make_wave_df(days)
        monkeypatch.setattr(svc.stock_service, 'get_stock_data',
                            lambda *a, **k: df.copy())
        return svc

    def test_structure_and_grid_sizes(self, monkeypatch):
        """各策略组合数符合网格定义；字段齐全；按sharpe降序"""
        expected_n = {'linear': 9, 'nonlinear': 9, 'macd': 8}
        for strat, n in expected_n.items():
            svc = self._svc_with_mock(monkeypatch)
            r = svc.optimize('FAKE', strat, market='US')
            assert 'error' not in r, r.get('error')
            assert len(r['results']) == n
            required = {'params', 'total_return', 'annual_return', 'max_drawdown',
                        'sharpe_ratio', 'win_rate', 'trade_count', 'final_value'}
            for row in r['results']:
                assert required.issubset(row.keys())
            sharpes = [row['sharpe_ratio'] for row in r['results']]
            assert sharpes == sorted(sharpes, reverse=True)

    def test_best_is_metric_max(self, monkeypatch):
        """best必须是results中metric最大者"""
        svc = self._svc_with_mock(monkeypatch)
        r = svc.optimize('FAKE', 'linear', market='US')
        max_sharpe = max(row['sharpe_ratio'] for row in r['results'])
        assert r['best']['sharpe_ratio'] == max_sharpe
        assert r['best']['params'] == \
            [row for row in r['results'] if row['sharpe_ratio'] == max_sharpe][0]['params']

    def test_heatmap_dims_and_mapping(self, monkeypatch):
        """heatmap z维度=x_len×y_len；z[y_idx][x_idx]与对应params的result行一致"""
        svc = self._svc_with_mock(monkeypatch)
        r = svc.optimize('FAKE', 'linear', market='US')
        hm = r['heatmap']
        assert hm['x_name'] == 'tp' and hm['y_name'] == 'sl'
        assert hm['x_values'] == sorted(PARAM_GRIDS['linear']['tp'])
        assert hm['y_values'] == sorted(PARAM_GRIDS['linear']['sl'])
        assert len(hm['z']) == len(hm['y_values'])           # 行数=y
        assert all(len(row) == len(hm['x_values']) for row in hm['z'])  # 列数=x
        # 抽查映射：z[1][2] 应等于 (tp=x[2], sl=y[1]) 那个组合的sharpe
        target = [row for row in r['results']
                  if row['params']['tp'] == hm['x_values'][2]
                  and row['params']['sl'] == hm['y_values'][1]][0]
        assert hm['z'][1][2] == target['sharpe_ratio']

    def test_heatmap_macd_signal9_slice(self, monkeypatch):
        """macd三维网格：results保留全部8组合，热力图固定signal=9取fast×slow切片"""
        svc = self._svc_with_mock(monkeypatch)
        r = svc.optimize('FAKE', 'macd', market='US')
        assert len(r['results']) == 8
        hm = r['heatmap']
        assert hm['x_name'] == 'fast' and hm['y_name'] == 'slow'
        assert len(hm['z']) == 2 and len(hm['z'][0]) == 2
        slice_params = {(p['fast'], p['slow'])
                        for p in (row['params'] for row in r['results'])
                        if p['signal'] == 9}
        assert len(slice_params) == 4  # 切片恰好覆盖2×2
        # 切片单元格值与signal=9的组合一致
        lookup = {(row['params']['fast'], row['params']['slow']): row['sharpe_ratio']
                  for row in r['results'] if row['params']['signal'] == 9}
        for yi, sv in enumerate(hm['y_values']):
            for xi, fv in enumerate(hm['x_values']):
                assert hm['z'][yi][xi] == lookup[(fv, sv)]

    def test_ma_cross_grid_filters_invalid(self, monkeypatch):
        """所有返回组合均满足 fast < slow"""
        svc = self._svc_with_mock(monkeypatch)
        r = svc.optimize('FAKE', 'ma_cross', market='US')
        assert all(row['params']['fast'] < row['params']['slow']
                   for row in r['results'])

    def test_metric_and_grid_overrides(self, monkeypatch):
        """metric切换排序依据；param_grid可覆盖部分键"""
        svc = self._svc_with_mock(monkeypatch)
        r = svc.optimize('FAKE', 'linear', market='US',
                         metric='total_return', param_grid={'tp': [0.12]})
        assert r['metric'] == 'total_return'
        tps = {row['params']['tp'] for row in r['results']}
        assert tps == {0.12}
        rets = [row['total_return'] for row in r['results']]
        assert rets == sorted(rets, reverse=True)
        max_ret = max(rets)
        assert r['best']['total_return'] == max_ret

    def test_max_drawdown_metric_sorts_ascending(self, monkeypatch):
        """按max_drawdown寻优时best必须是回撤最小者（回归：曾经降序取到回撤最大者）"""
        svc = self._svc_with_mock(monkeypatch)
        r = svc.optimize('FAKE', 'linear', market='US', metric='max_drawdown')
        dds = [row['max_drawdown'] for row in r['results']]
        # 回撤为负数（越低=回撤越大），升序后第一名是最大值
        assert dds == sorted(dds)
        min_dd = min(dds)
        assert r['best']['max_drawdown'] == min_dd
        assert r['best']['params'] == \
            [row for row in r['results'] if row['max_drawdown'] == min_dd][0]['params']

    def test_unknown_strategy_or_metric(self, monkeypatch):
        svc = self._svc_with_mock(monkeypatch)
        assert 'error' in svc.optimize('FAKE', 'bogus')
        assert 'error' in svc.optimize('FAKE', 'linear', metric='bogus')

    def test_insufficient_data(self, monkeypatch):
        svc = BacktestService()
        df = make_wave_df(40)  # 少于50根K线
        monkeypatch.setattr(svc.stock_service, 'get_stock_data',
                            lambda *a, **k: df.copy())
        assert 'error' in svc.optimize('FAKE', 'linear')


# ============================================
# walk_forward 滚动验证
# ============================================
class TestWalkForward:
    def _svc_with_mock(self, monkeypatch, days: int = 630) -> BacktestService:
        svc = BacktestService()
        df = make_wave_df(days)
        monkeypatch.setattr(svc.stock_service, 'get_stock_data',
                            lambda *a, **k: df.copy())
        return svc

    def test_two_segment_structure(self, monkeypatch):
        """2段验证：分段数/步号/区间顺序正确，summary数学一致"""
        svc = self._svc_with_mock(monkeypatch)
        wf = svc.walk_forward('FAKE', 'linear', market='US', segments=2)
        assert 'error' not in wf
        assert len(wf['segments']) == 2
        assert [s['step'] for s in wf['segments']] == [1, 2]
        # 训练区间整体早于测试区间（无前视）
        for s in wf['segments']:
            assert s['train_range'][1] <= s['test_range'][0]
            assert set(s.keys()) >= {
                'step', 'train_range', 'test_range', 'best_params', 'is_sharpe',
                'oos_return', 'oos_sharpe', 'oos_max_drawdown',
                'oos_buy_hold_return', 'beats_buy_hold'}
        summary = wf['summary']
        assert summary['total_segments'] == 2
        assert summary['win_segments'] == \
            sum(1 for s in wf['segments'] if s['beats_buy_hold'])
        assert abs(summary['avg_oos_return']
                   - round(float(np.mean([s['oos_return'] for s in wf['segments']])), 2)) <= 0.01

    def test_stitched_curve_length_and_continuity(self, monkeypatch):
        """OOS拼接曲线长度=各测试段equity长度之和；段边界处新段首值==前段末值"""
        days = 630
        svc = self._svc_with_mock(monkeypatch, days)
        wf = svc.walk_forward('FAKE', 'linear', market='US', segments=2)
        block = days // 3  # segments+1=3等长块，末块吸收余数
        seg_lens = [block - 1, days - 2 * block - 1]  # 各测试段start=1的曲线长度
        stitched = wf['stitched_oos_curve']
        assert len(stitched) == sum(seg_lens)

        # 段边界连续：第2段首点==第1段末点（rebase系数=本段初值/本段初值）
        boundary = seg_lens[0]
        assert stitched[boundary]['value'] == stitched[boundary - 1]['value']

        # 日期严格递增（各测试块时间上连续不重叠）
        dates = [p['date'] for p in stitched]
        assert all(dates[i] < dates[i + 1] for i in range(len(dates) - 1))

    def test_beats_flag_consistency(self, monkeypatch):
        """beats_buy_hold 必须与报告的 oos_return/oos_buy_hold_return 自洽"""
        svc = self._svc_with_mock(monkeypatch)
        wf = svc.walk_forward('FAKE', 'nonlinear', market='US', segments=3)
        for s in wf['segments']:
            assert s['beats_buy_hold'] == (s['oos_return'] > s['oos_buy_hold_return'])

    def test_train_ratio_one_is_anchored_blocks(self, monkeypatch):
        """train_ratio=1 时训练窗起点回到块0（完整锚定窗口 块[0..i-1]）"""
        svc = self._svc_with_mock(monkeypatch)
        wf = svc.walk_forward('FAKE', 'ma_cross', market='US',
                              segments=3, train_ratio=1.0)
        first_starts = {s['step']: s['train_range'][0] for s in wf['segments']}
        # 三步的训练窗都从数据第一天开始
        assert len(set(first_starts.values())) == 1

    def test_validation_errors(self, monkeypatch):
        """segments越界/未知策略/数据过短均报错"""
        svc = self._svc_with_mock(monkeypatch)
        assert 'error' in svc.walk_forward('FAKE', 'linear', segments=0)
        assert 'error' in svc.walk_forward('FAKE', 'linear', segments=5)
        assert 'error' in svc.walk_forward('FAKE', 'bogus')
        short = BacktestService()
        df = make_wave_df(150)  # 60*(2+1)=180不够
        monkeypatch.setattr(short.stock_service, 'get_stock_data',
                            lambda *a, **k: df.copy())
        assert 'error' in short.walk_forward('FAKE', 'linear', segments=2)


# ============================================
# Schema 默认值
# ============================================
class TestSchemas:
    def test_optimize_request_defaults(self):
        from app.schemas import OptimizeRequest
        req = OptimizeRequest(stock_code='MU', strategy='linear')
        assert req.period == '1y'
        assert req.initial_capital == 100000
        assert req.commission_per_trade == 1.0
        assert req.metric == 'sharpe'
        assert req.param_grid is None

    def test_walkforward_request_defaults(self):
        from app.schemas import WalkForwardRequest
        req = WalkForwardRequest(stock_code='600519', strategy='macd')
        assert req.period == '5y'
        assert req.initial_capital == 100000
        assert req.commission_per_trade == 1.0
        assert req.train_ratio == 0.6
        assert req.segments == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
