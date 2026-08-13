"""
真实数据回测示例
演示如何获取真实美股数据并进行回测
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime

from utils.data_fetcher import USStockDataFetcher, fetch_stock_data, fetch_multiple_stocks
from utils.indicators import add_all_indicators
from strategies.trend_following import (
    DualMovingAverage,
    MACDStrategy,
    RSIStrategy,
    SuperTrendStrategy,
    backtest_strategy
)
from strategies.multi_factor import MultiStockSelector
from utils.visualization import plot_backtest_results, plot_strategy_comparison


def demo_single_stock():
    """示例1: 单只股票回测"""
    print("\n" + "="*60)
    print("示例1: 单只股票回测 (苹果 AAPL)")
    print("="*60)

    # 获取数据
    print("\n正在获取 AAPL 数据...")
    df = fetch_stock_data('AAPL', period='1y')

    if df.empty:
        print("无法获取数据，请检查网络连接")
        return None

    # 清理数据
    df = df.dropna()
    df['Close'] = df['Close'].astype(float)

    print(f"获取到 {len(df)} 条数据")
    print(f"时间范围: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"起始价格: ${df['Close'].iloc[0]:.2f}")
    print(f"结束价格: ${df['Close'].iloc[-1]:.2f}")
    print(f"期间涨幅: {(df['Close'].iloc[-1]/df['Close'].iloc[0]-1)*100:.2f}%")

    # 测试双均线策略
    print("\n运行双均线策略 (20/50)...")
    strategy = DualMovingAverage(short_period=20, long_period=50)
    results, stats = backtest_strategy(df, strategy)

    print(f"\n策略回测结果:")
    print(f"   年化收益率: {stats['annual_return']*100:.2f}%")
    print(f"   最大回撤: {stats['max_drawdown']*100:.2f}%")
    print(f"   夏普比率: {stats['sharpe_ratio']:.2f}")
    print(f"   交易次数: {stats['n_trades']}")
    print(f"   最终资金: ${stats['final_value']:,.2f}")

    return results, stats


def demo_strategy_comparison():
    """示例2: 多策略对比"""
    print("\n" + "="*60)
    print("示例2: 多策略对比 (AAPL)")
    print("="*60)

    # 获取数据
    df = fetch_stock_data('AAPL', period='2y')
    if df.empty:
        print("无法获取数据")
        return None

    df = add_all_indicators(df)

    # 定义策略
    strategies = {
        'Dual MA (20/50)': DualMovingAverage(short_period=20, long_period=50),
        'Dual MA (10/30)': DualMovingAverage(short_period=10, long_period=30),
        'MACD': MACDStrategy(fast=12, slow=26, signal=9),
        'RSI': RSIStrategy(period=14, oversold=30, overbought=70),
        'SuperTrend': SuperTrendStrategy(period=10, multiplier=3.0),
    }

    # 回测所有策略
    results = {}
    stats_comparison = {}

    print("\n回测结果对比:")
    print("-" * 60)
    print(f"{'策略':<20} {'年化收益':>10} {'最大回撤':>10} {'夏普比率':>10}")
    print("-" * 60)

    for name, strategy in strategies.items():
        results[name], stats = backtest_strategy(df, strategy)
        stats_comparison[name] = stats
        print(f"{name:<20} {stats['annual_return']*100:>9.2f}% {stats['max_drawdown']*100:>9.2f}% {stats['sharpe_ratio']:>10.2f}")

    # 找出最优策略
    best_name = max(stats_comparison.keys(), key=lambda x: stats_comparison[x]['sharpe_ratio'])
    print("-" * 60)
    print(f"\n最优策略: {best_name}")
    print(f"   夏普比率: {stats_comparison[best_name]['sharpe_ratio']:.2f}")

    return results, stats_comparison


def demo_multi_stock_selection():
    """示例3: 多股票选择"""
    print("\n" + "="*60)
    print("示例3: 多股票选择 (科技股)")
    print("="*60)

    # 股票池
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']

    print(f"\n正在获取 {len(symbols)} 只股票数据...")
    data_dict = fetch_multiple_stocks(symbols, period='1y')

    if not data_dict:
        print("无法获取数据")
        return None

    print(f"\n成功获取 {len(data_dict)} 只股票数据")

    # 多股票选择器
    selector = MultiStockSelector(n_stocks=3)
    rankings = selector.rank_stocks(data_dict)

    print("\n股票排名 (按综合评分):")
    print("-" * 60)
    print(f"{'排名':<5} {'股票':<8} {'评分':>8} {'20日动量':>10} {'60日动量':>10}")
    print("-" * 60)

    for i, (_, row) in enumerate(rankings.head(5).iterrows()):
        print(f"{i+1:<5} {row['Symbol']:<8} {row['Score']:>8.4f} {row['Momentum_20']*100:>9.2f}% {row['Momentum_60']*100:>9.2f}%")

    # 选择投资组合
    weights = selector.select_portfolio(data_dict, 'momentum')
    print("\n投资组合配置:")
    print("-" * 60)
    for symbol, weight in weights.items():
        print(f"   {symbol}: {weight*100:.2f}%")

    return rankings, weights


def demo_save_and_load():
    """示例4: 数据保存和加载"""
    print("\n" + "="*60)
    print("示例4: 数据保存和加载")
    print("="*60)

    fetcher = USStockDataFetcher()

    # 获取数据
    print("\n获取 MSFT 数据...")
    df = fetcher.get_stock_data('MSFT', period='1y')

    if df.empty:
        print("无法获取数据")
        return None

    # 保存数据
    filepath = fetcher.save_data(df, 'MSFT')
    print(f"数据已保存到: {filepath}")

    # 从本地加载
    df_loaded = fetcher.load_data('MSFT')
    print(f"从本地加载: {len(df_loaded)} 条数据")

    # 验证数据一致性
    if len(df) == len(df_loaded):
        print("数据一致性验证通过!")
    else:
        print("警告: 数据长度不一致")

    return df, df_loaded


def demo_parameter_optimization():
    """示例5: 参数优化"""
    print("\n" + "="*60)
    print("示例5: 参数优化 (AAPL)")
    print("="*60)

    # 获取数据
    df = fetch_stock_data('AAPL', period='2y')
    if df.empty:
        print("无法获取数据")
        return None

    df = add_all_indicators(df)

    # 参数网格
    param_grid = {
        'short_period': [10, 15, 20, 25, 30],
        'long_period': [40, 50, 60, 70, 80]
    }

    print("\n正在优化参数...")
    print(f"短期均线范围: {param_grid['short_period']}")
    print(f"长期均线范围: {param_grid['long_period']}")

    # 遍历所有组合
    results_list = []
    total_combinations = 0

    for short in param_grid['short_period']:
        for long in param_grid['long_period']:
            if short >= long:
                continue

            total_combinations += 1
            strategy = DualMovingAverage(short_period=short, long_period=long)
            _, stats = backtest_strategy(df, strategy)

            results_list.append({
                'short': short,
                'long': long,
                'sharpe': stats['sharpe_ratio'],
                'return': stats['annual_return'],
                'drawdown': stats['max_drawdown']
            })

    print(f"\n共测试 {total_combinations} 种参数组合")

    # 找出最优
    results_df = pd.DataFrame(results_list)
    results_df = results_df.sort_values('sharpe', ascending=False)

    print("\nTop 5 参数组合 (按夏普比率排序):")
    print("-" * 60)
    print(f"{'短期':>6} {'长期':>6} {'夏普比率':>10} {'年化收益':>10} {'最大回撤':>10}")
    print("-" * 60)

    for _, row in results_df.head(5).iterrows():
        print(f"{int(row['short']):>6} {int(row['long']):>6} {row['sharpe']:>10.2f} {row['return']*100:>9.2f}% {row['drawdown']*100:>9.2f}%")

    # 最优参数
    best = results_df.iloc[0]
    print("-" * 60)
    print(f"\n最优参数: 短期={int(best['short'])}, 长期={int(best['long'])}")
    print(f"   夏普比率: {best['sharpe']:.2f}")
    print(f"   年化收益: {best['return']*100:.2f}%")

    return results_df


def run_all_demos():
    """运行所有示例"""
    print("\n" + "#"*60)
    print("    真实数据回测示例")
    print("#"*60)

    try:
        # 示例1
        demo_single_stock()

        # 示例2
        demo_strategy_comparison()

        # 示例3
        demo_multi_stock_selection()

        # 示例4
        demo_save_and_load()

        # 示例5
        demo_parameter_optimization()

        # 总结
        print("\n" + "#"*60)
        print("所有示例运行完成!")
        print("#"*60)
        print("\n下一步:")
        print("   1. 尝试修改股票代码进行测试")
        print("   2. 调整策略参数")
        print("   3. 开发自己的策略")

    except Exception as e:
        print(f"\n运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_demos()
