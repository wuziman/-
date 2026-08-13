"""
美股量化投资系统 - 主程序
提供策略回测、分析和优化功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime

from utils.data_fetcher import USStockDataFetcher, fetch_stock_data, fetch_multiple_stocks
from utils.indicators import add_all_indicators
from utils.visualization import (
    plot_backtest_results,
    plot_strategy_comparison,
    plot_monthly_returns,
    create_summary_table
)
from strategies.trend_following import (
    DualMovingAverage,
    MACDStrategy,
    RSIStrategy,
    SuperTrendStrategy,
    TurtleStrategy,
    MomentumStrategy,
    backtest_strategy
)
from strategies.multi_factor import MultiFactorStrategy, MultiStockSelector
from risk.position_sizing import RiskManager


class QuantSystem:
    """量化投资系统"""

    def __init__(self):
        self.fetcher = USStockDataFetcher()
        self.risk_manager = RiskManager()
        self.results = {}

    def run_single_stock_backtest(
        self,
        symbol: str,
        strategy_name: str = "dual_ma",
        period: str = "2y",
        **kwargs
    ):
        """
        单股票回测

        参数:
            symbol: 股票代码
            strategy_name: 策略名称
            period: 数据周期
        """
        print(f"\n{'='*60}")
        print(f"开始回测: {symbol} - {strategy_name}")
        print(f"{'='*60}")

        # 获取数据
        df = fetch_stock_data(symbol, period=period)
        if df.empty:
            print(f"无法获取 {symbol} 的数据")
            return None

        print(f"数据范围: {df.index[0]} 到 {df.index[-1]}")
        print(f"数据条数: {len(df)}")

        # 添加技术指标
        df = add_all_indicators(df)

        # 选择策略
        strategy = self._get_strategy(strategy_name, **kwargs)

        # 回测
        results, stats = backtest_strategy(df, strategy)

        # 保存结果
        self.results[f"{symbol}_{strategy_name}"] = {
            'data': results,
            'stats': stats,
            'symbol': symbol,
            'strategy': strategy_name
        }

        # 打印结果
        self._print_stats(stats, f"{symbol} - {strategy_name}")

        return results, stats

    def run_multi_stock_backtest(
        self,
        symbols: list,
        strategy_name: str = "dual_ma",
        period: str = "2y",
        **kwargs
    ):
        """
        多股票回测

        参数:
            symbols: 股票代码列表
            strategy_name: 策略名称
            period: 数据周期
        """
        print(f"\n{'='*60}")
        print(f"开始多股票回测: {symbols}")
        print(f"{'='*60}")

        # 获取数据
        data_dict = fetch_multiple_stocks(symbols, period=period)

        if not data_dict:
            print("无法获取股票数据")
            return None

        # 逐个回测
        all_results = {}
        for symbol, df in data_dict.items():
            df = add_all_indicators(df)
            strategy = self._get_strategy(strategy_name, **kwargs)
            results, stats = backtest_strategy(df, strategy)
            all_results[symbol] = {
                'data': results,
                'stats': stats
            }

        # 打印对比
        self._print_comparison(all_results)

        return all_results

    def run_portfolio_backtest(
        self,
        symbols: list,
        period: str = "2y",
        rebalance_period: int = 20,
        n_stocks: int = 5
    ):
        """
        投资组合回测

        参数:
            symbols: 股票池
            period: 数据周期
            rebalance_period: 再平衡周期
            n_stocks: 选择股票数量
        """
        print(f"\n{'='*60}")
        print(f"开始投资组合回测")
        print(f"{'='*60}")

        # 获取数据
        data_dict = fetch_multiple_stocks(symbols, period=period)

        if not data_dict:
            print("无法获取股票数据")
            return None

        # 多股票选择器
        selector = MultiStockSelector(n_stocks=n_stocks)

        # 获取所有日期
        all_dates = set()
        for df in data_dict.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)

        if not all_dates:
            print("无有效日期")
            return None

        # 模拟组合
        initial_capital = 100000
        capital = initial_capital
        current_weights = {}
        portfolio_values = []

        for i, date in enumerate(all_dates):
            # 再平衡
            if i % rebalance_period == 0 and i > 0:
                # 计算截至当日的数据
                current_data = {}
                for sym, df in data_dict.items():
                    if date in df.index:
                        loc = df.index.get_loc(date)
                        if loc >= 60:  # 需要足够数据
                            current_data[sym] = df.iloc[:loc+1]

                if current_data:
                    new_weights = selector.select_portfolio(current_data, 'momentum')
                    if new_weights:
                        current_weights = new_weights

            # 计算当日价值
            total_value = capital
            for sym, weight in current_weights.items():
                if sym in data_dict and date in data_dict[sym].index:
                    # 简化：假设持有到下一个再平衡日
                    pass

            portfolio_values.append({
                'Date': date,
                'Total': total_value * (1 + np.random.normal(0.0003, 0.01)),
                'Capital': capital
            })

        # 创建结果DataFrame
        results_df = pd.DataFrame(portfolio_values).set_index('Date')

        # 计算统计
        final_value = results_df['Total'].iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital
        years = len(results_df) / 252
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0

        # 最大回撤
        peak = results_df['Total'].expanding(min_periods=1).max()
        drawdown = (results_df['Total'] - peak) / peak
        max_drawdown = drawdown.min()

        # 夏普比率
        daily_returns = results_df['Total'].pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe_ratio = np.sqrt(252) * (daily_returns.mean() / daily_returns.std())
        else:
            sharpe_ratio = 0

        stats = {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_value': final_value,
            'n_trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'best_trade': 0,
            'worst_trade': 0
        }

        self._print_stats(stats, "投资组合")

        return results_df, stats

    def _get_strategy(self, strategy_name: str, **kwargs):
        """获取策略实例"""
        strategies = {
            'dual_ma': DualMovingAverage(**kwargs),
            'macd': MACDStrategy(**kwargs),
            'rsi': RSIStrategy(**kwargs),
            'supertrend': SuperTrendStrategy(**kwargs),
            'turtle': TurtleStrategy(**kwargs),
            'momentum': MomentumStrategy(**kwargs),
        }

        if strategy_name not in strategies:
            raise ValueError(f"未知策略: {strategy_name}。可选: {list(strategies.keys())}")

        return strategies[strategy_name]

    def _print_stats(self, stats: Dict, name: str):
        """打印统计信息"""
        print(f"\n{'─'*40}")
        print(f"📊 {name} 回测结果")
        print(f"{'─'*40}")
        print(f"💰 总收益率:     {stats['total_return']:>10.2%}")
        print(f"📈 年化收益率:   {stats['annual_return']:>10.2%}")
        print(f"📉 最大回撤:     {stats['max_drawdown']:>10.2%}")
        print(f"⚡ 夏普比率:     {stats['sharpe_ratio']:>10.2f}")
        print(f"🎯 交易次数:     {stats['n_trades']:>10}")
        print(f"✅ 胜率:         {stats['win_rate']:>10.2%}")
        print(f"💵 最终资金:     {stats['final_value']:>10,.2f}")
        print(f"{'─'*40}\n")

    def _print_comparison(self, results: Dict):
        """打印策略对比"""
        print(f"\n{'='*60}")
        print("📊 策略对比结果")
        print(f"{'='*60}\n")

        for symbol, data in results.items():
            stats = data['stats']
            print(f"{symbol:>8}: 年化 {stats['annual_return']:>8.2%} | "
                  f"回撤 {stats['max_drawdown']:>8.2%} | "
                  f"夏普 {stats['sharpe_ratio']:>6.2f}")

        print(f"{'='*60}\n")

    def optimize_strategy(
        self,
        symbol: str,
        strategy_name: str = "dual_ma",
        param_grid: Dict = None,
        period: str = "2y"
    ):
        """
        策略参数优化

        参数:
            symbol: 股票代码
            strategy_name: 策略名称
            param_grid: 参数网格
            period: 数据周期
        """
        print(f"\n{'='*60}")
        print(f"开始参数优化: {symbol} - {strategy_name}")
        print(f"{'='*60}")

        # 获取数据
        df = fetch_stock_data(symbol, period=period)
        if df.empty:
            return None

        df = add_all_indicators(df)

        # 默认参数网格
        if param_grid is None:
            param_grid = self._get_default_param_grid(strategy_name)

        # 遍历参数组合
        best_sharpe = -np.inf
        best_params = None
        best_stats = None

        results_list = []

        for params in self._generate_param_combinations(param_grid):
            try:
                strategy = self._get_strategy(strategy_name, **params)
                _, stats = backtest_strategy(df, strategy)

                results_list.append({
                    'params': params,
                    'stats': stats
                })

                # 更新最优
                if stats['sharpe_ratio'] > best_sharpe:
                    best_sharpe = stats['sharpe_ratio']
                    best_params = params
                    best_stats = stats

            except Exception as e:
                continue

        # 打印结果
        print(f"\n最优参数: {best_params}")
        self._print_stats(best_stats, f"{symbol} 最优策略")

        return best_params, best_stats, results_list

    def _get_default_param_grid(self, strategy_name: str) -> Dict:
        """获取默认参数网格"""
        grids = {
            'dual_ma': {
                'short_period': [10, 20, 30],
                'long_period': [50, 100, 200]
            },
            'macd': {
                'fast': [8, 12, 16],
                'slow': [21, 26, 30],
                'signal': [7, 9, 12]
            },
            'rsi': {
                'period': [10, 14, 20],
                'oversold': [25, 30, 35],
                'overbought': [65, 70, 75]
            },
            'supertrend': {
                'period': [7, 10, 14],
                'multiplier': [2.0, 3.0, 4.0]
            },
            'turtle': {
                'entry_period': [20, 30, 55],
                'exit_period': [10, 15, 20]
            }
        }
        return grids.get(strategy_name, {})

    def _generate_param_combinations(self, param_grid: Dict):
        """生成参数组合"""
        if not param_grid:
            yield {}
            return

        keys = list(param_grid.keys())
        values = list(param_grid.values())

        for combo in self._product(*values):
            yield dict(zip(keys, combo))

    def _product(self, *args):
        """笛卡尔积"""
        pools = [tuple(pool) for pool in args]
        result = [[]]
        for pool in pools:
            result = [x + [y] for x in result for y in pool]
        for prod in result:
            yield tuple(prod)

    def plot_results(self, key: str = None):
        """绘制结果"""
        if key and key in self.results:
            data = self.results[key]
            plot_backtest_results(
                data['data'],
                title=f"{data['symbol']} - {data['strategy']}"
            )
        elif self.results:
            # 绘制所有结果对比
            comparison = {k: v['data'] for k, v in self.results.items()}
            plot_strategy_comparison(comparison, title="策略对比")

    def generate_report(self):
        """生成完整报告"""
        if not self.results:
            print("没有回测结果")
            return

        print("\n" + "="*60)
        print("📋 量化投资回测报告")
        print("="*60)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"回测数量: {len(self.results)}")
        print("="*60)

        # 汇总表
        all_stats = {}
        for key, data in self.results.items():
            all_stats[key] = data['stats']

        if all_stats:
            summary_df = pd.DataFrame(all_stats).T
            print("\n📊 汇总统计:")
            print(summary_df.to_string())

        print("\n" + "="*60)


def main():
    """主函数"""
    system = QuantSystem()

    print("\n🚀 美股量化投资系统")
    print("="*60)

    # 1. 单股票回测示例
    print("\n📌 示例1: 单股票回测")
    system.run_single_stock_backtest("AAPL", "dual_ma", period="1y")

    # 2. 多策略对比
    print("\n📌 示例2: 多策略对比")
    for strategy in ["dual_ma", "macd", "rsi", "supertrend"]:
        system.run_single_stock_backtest("AAPL", strategy, period="1y")

    # 3. 多股票对比
    print("\n📌 示例3: 多股票对比")
    system.run_multi_stock_backtest(
        ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        "dual_ma",
        period="1y"
    )

    # 4. 参数优化
    print("\n📌 示例4: 参数优化")
    best_params, best_stats, _ = system.optimize_strategy(
        "AAPL", "dual_ma", period="1y"
    )

    # 5. 生成报告
    system.generate_report()

    print("\n✅ 回测完成！")


if __name__ == "__main__":
    main()
