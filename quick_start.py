"""
快速入门指南
帮助你快速开始使用量化投资系统
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime


def create_sample_data():
    """创建模拟数据（当无法获取真实数据时使用）"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='B')
    n = len(dates)

    price = 100
    prices = []
    trend = 1

    for i in range(n):
        if i % 100 == 0:
            trend = np.random.choice([1, -1])
        change = np.random.normal(0.001 * trend, 0.015)
        price = price * (1 + change)
        prices.append(price)

    df = pd.DataFrame({
        'Open': prices * (1 + np.random.uniform(-0.01, 0.01, n)),
        'High': prices * (1 + np.random.uniform(0, 0.02, n)),
        'Low': prices * (1 - np.random.uniform(0, 0.02, n)),
        'Close': prices,
        'Volume': np.random.randint(10000000, 50000000, n)
    }, index=dates)
    df.index.name = 'Date'

    return df


def example_1_basic_backtest():
    """示例1: 基础回测"""
    print("\n" + "="*60)
    print("示例1: 基础回测")
    print("="*60)

    from strategies.trend_following import DualMovingAverage, backtest_strategy

    # 创建数据
    df = create_sample_data()

    # 创建策略
    strategy = DualMovingAverage(short_period=20, long_period=50)

    # 回测
    results, stats = backtest_strategy(df, strategy)

    # 打印结果
    print(f"\n[OK] 回测完成!")
    print(f"   年化收益率: {stats['annual_return']:.2%}")
    print(f"   最大回撤: {stats['max_drawdown']:.2%}")
    print(f"   夏普比率: {stats['sharpe_ratio']:.2f}")

    return results, stats


def example_2_strategy_comparison():
    """示例2: 策略对比"""
    print("\n" + "="*60)
    print("示例2: 策略对比")
    print("="*60)

    from strategies.trend_following import (
        DualMovingAverage,
        MACDStrategy,
        RSIStrategy,
        backtest_strategy
    )

    # 创建数据
    df = create_sample_data()

    # 定义策略
    strategies = {
        '双均线 (20/50)': DualMovingAverage(short_period=20, long_period=50),
        'MACD (12/26/9)': MACDStrategy(fast=12, slow=26, signal=9),
        'RSI (14)': RSIStrategy(period=14, oversold=30, overbought=70),
    }

    # 回测所有策略
    results = {}
    stats_dict = {}
    for name, strategy in strategies.items():
        results[name], stats = backtest_strategy(df, strategy)
        stats_dict[name] = stats
        print(f"\n{name}:")
        print(f"   年化收益率: {stats['annual_return']:.2%}")
        print(f"   最大回撤: {stats['max_drawdown']:.2%}")
        print(f"   夏普比率: {stats['sharpe_ratio']:.2f}")

    # 找出最优策略
    best_name = max(stats_dict.keys(), key=lambda x: stats_dict[x]['sharpe_ratio'])
    print(f"\n最优策略: {best_name}")

    return results


def example_3_parameter_optimization():
    """示例3: 参数优化"""
    print("\n" + "="*60)
    print("示例3: 参数优化")
    print("="*60)

    from strategies.trend_following import DualMovingAverage, backtest_strategy

    # 创建数据
    df = create_sample_data()

    # 定义参数网格
    param_grid = {
        'short_period': [10, 15, 20, 25, 30],
        'long_period': [40, 50, 60, 70, 80]
    }

    # 遍历所有组合
    best_sharpe = -np.inf
    best_params = None
    best_stats = None

    for short in param_grid['short_period']:
        for long in param_grid['long_period']:
            if short >= long:
                continue

            strategy = DualMovingAverage(short_period=short, long_period=long)
            _, stats = backtest_strategy(df, strategy)

            if stats['sharpe_ratio'] > best_sharpe:
                best_sharpe = stats['sharpe_ratio']
                best_params = {'short_period': short, 'long_period': long}
                best_stats = stats

    print(f"\n[OK] 优化完成!")
    print(f"   最优短期均线: {best_params['short_period']} 天")
    print(f"   最优长期均线: {best_params['long_period']} 天")
    print(f"   最优年化收益率: {best_stats['annual_return']:.2%}")
    print(f"   最优夏普比率: {best_stats['sharpe_ratio']:.2f}")

    return best_params, best_stats


def example_4_risk_management():
    """示例4: 风险管理"""
    print("\n" + "="*60)
    print("示例4: 风险管理")
    print("="*60)

    from risk.position_sizing import PositionManager, StopLossManager

    # 1. 仓位管理
    pm = PositionManager()
    capital = 1000000  # 100万资金
    price = 150        # 股票价格
    stop_loss = 142.5  # 止损价（5%止损）

    shares = pm.calculate_position_size(capital, price, stop_loss, risk_per_trade=0.02)
    position_value = shares * price
    position_pct = position_value / capital

    print(f"\n仓位管理示例:")
    print(f"   资金: {capital:,.0f} 元")
    print(f"   股价: {price:.2f} 元")
    print(f"   止损价: {stop_loss:.2f} 元")
    print(f"   建议股数: {shares} 股")
    print(f"   仓位价值: {position_value:,.0f} 元")
    print(f"   仓位比例: {position_pct:.2%}")

    # 2. 止损管理
    slm = StopLossManager(initial_stop_pct=0.05, trailing_stop_pct=0.10)
    entry_price = 100
    highest_price = 115
    current_price = 108

    initial_stop = slm.calculate_initial_stop(entry_price)
    trailing_stop = slm.calculate_trailing_stop(entry_price, highest_price)

    print(f"\n止损管理示例:")
    print(f"   入场价: {entry_price:.2f} 元")
    print(f"   最高价: {highest_price:.2f} 元")
    print(f"   当前价: {current_price:.2f} 元")
    print(f"   初始止损: {initial_stop:.2f} 元")
    print(f"   移动止损: {trailing_stop:.2f} 元")
    print(f"   当前止损状态: {'触发' if current_price <= trailing_stop else '未触发'}")


def example_5_visualization():
    """示例5: 可视化"""
    print("\n" + "="*60)
    print("示例5: 可视化")
    print("="*60)

    from strategies.trend_following import DualMovingAverage, backtest_strategy
    from utils.visualization import plot_backtest_results

    # 创建数据
    df = create_sample_data()

    # 回测
    strategy = DualMovingAverage(short_period=20, long_period=50)
    results, stats = backtest_strategy(df, strategy)

    # 绘图
    print("\n正在生成图表...")
    try:
        plot_backtest_results(results, title="AAPL 双均线策略", save_path="backtest_result.png")
        print("[OK] 图表已保存: backtest_result.png")
    except Exception as e:
        print(f"[WARN] 图表生成失败（可能没有显示环境）: {e}")
        print("   但回测结果是正确的!")


def run_all_examples():
    """运行所有示例"""
    print("\n" + "="*60)
    print("    美股量化投资系统 - 快速入门")
    print("="*60)

    try:
        # 示例1
        example_1_basic_backtest()

        # 示例2
        example_2_strategy_comparison()

        # 示例3
        example_3_parameter_optimization()

        # 示例4
        example_4_risk_management()

        # 示例5
        example_5_visualization()

        # 总结
        print("\n" + "="*60)
        print("[OK] 所有示例运行完成!")
        print("="*60)
        print("\n下一步:")
        print("   1. 阅读 README.md 了解详细功能")
        print("   2. 修改 main.py 中的参数进行自定义回测")
        print("   3. 尝试获取真实数据进行回测")
        print("   4. 开发自己的策略!")

    except Exception as e:
        print(f"\n[ERROR] 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_examples()
