"""
自选股完整分析脚本
一键分析 MU、SNDK、SOXL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from utils.data_fetcher import USStockDataFetcher
from strategies.trend_following import (
    DualMovingAverage, MACDStrategy,
    RSIStrategy, SuperTrendStrategy,
    backtest_strategy
)
from risk.position_sizing import PositionManager


def analyze_stock(symbol, folder, strategy_name='dual_ma'):
    """分析单只股票"""
    print(f"\n{'='*60}")
    print(f"  分析: {symbol}")
    print(f"{'='*60}")

    # 加载数据
    fetcher = USStockDataFetcher(data_dir=f'./{folder}')
    df = fetcher.load_data(symbol)

    if df.empty:
        print(f"  无法加载 {symbol} 数据")
        return None

    # 基本信息
    print(f"\n[INFO] 基本信息:")
    print(f"  数据范围: {df.index[0].date()} 到 {df.index[-1].date()}")
    print(f"  数据条数: {len(df)}")
    print(f"  当前价格: ${df['Close'].iloc[-1]:.2f}")
    print(f"  52周最高: ${df['High'].max():.2f}")
    print(f"  52周最低: ${df['Low'].min():.2f}")

    # 测试多个策略
    print(f"\n[STRATEGY] 策略回测:")
    print("-" * 60)

    strategies = {
        '双均线(20/50)': DualMovingAverage(20, 50),
        '双均线(10/30)': DualMovingAverage(10, 30),
        'MACD': MACDStrategy(12, 26, 9),
        'RSI': RSIStrategy(14, 30, 70),
        'SuperTrend': SuperTrendStrategy(10, 3.0),
    }

    results = {}
    for name, strategy in strategies.items():
        _, stats = backtest_strategy(df, strategy)
        results[name] = stats

    # 打印结果
    print(f"{'策略':<15} {'年化收益':>10} {'最大回撤':>10} {'夏普比率':>10}")
    print("-" * 60)
    for name, stats in results.items():
        print(f"{name:<15} {stats['annual_return']*100:>9.2f}% "
              f"{stats['max_drawdown']*100:>9.2f}% "
              f"{stats['sharpe_ratio']:>10.2f}")

    # 找出最优策略
    best_name = max(results.keys(), key=lambda x: results[x]['sharpe_ratio'])
    best_stats = results[best_name]

    print("-" * 60)
    print(f"\n[BEST] 最优策略: {best_name}")
    print(f"  年化收益: {best_stats['annual_return']*100:.2f}%")
    print(f"  最大回撤: {best_stats['max_drawdown']*100:.2f}%")
    print(f"  夏普比率: {best_stats['sharpe_ratio']:.2f}")

    return {
        'symbol': symbol,
        'current_price': df['Close'].iloc[-1],
        'best_strategy': best_name,
        'stats': best_stats
    }


def analyze_portfolio():
    """分析投资组合"""
    print("\n" + "="*60)
    print("  投资组合分析")
    print("="*60)

    # 定义股票
    stocks = [
        ('MU', 'MU_美光'),
        ('SNDK', 'SNDK_闪迪'),
        ('SOXL', 'SOXL_半导体ETF'),
    ]

    # 分析每只股票
    all_results = []
    for symbol, folder in stocks:
        result = analyze_stock(symbol, folder)
        if result:
            all_results.append(result)

    if not all_results:
        print("无法分析任何股票")
        return

    # 投资组合配置建议
    print("\n" + "="*60)
    print("  [PORTFOLIO] 投资组合配置建议")
    print("="*60)

    pm = PositionManager()
    capital = 1_000_000  # 假设100万资金

    print(f"\n假设资金: ${capital:,.0f}")
    print(f"单笔风险: 2%")
    print("-" * 60)

    total_allocation = 0
    for result in all_results:
        symbol = result['symbol']
        price = result['current_price']
        stop_price = price * 0.95  # 5%止损

        shares = pm.calculate_position_size(capital, price, stop_price, 0.02)
        value = shares * price
        pct = value / capital * 100
        total_allocation += pct

        print(f"{symbol}:")
        print(f"  当前价: ${price:.2f}")
        print(f"  建议股数: {shares}")
        print(f"  仓位价值: ${value:,.0f} ({pct:.1f}%)")
        print(f"  推荐策略: {result['best_strategy']}")
        print()

    print("-" * 60)
    print(f"总仓位: {total_allocation:.1f}%")
    print(f"现金: {100-total_allocation:.1f}%")

    # 风险提示
    print("\n" + "="*60)
    print("  [WARNING] 风险提示")
    print("="*60)
    print("""
1. 回测结果不代表未来收益
2. 杠杆ETF(SOXL)风险较高，适合短线
3. 建议分散投资，不要把所有资金投入一只股票
4. 设置止损，控制单笔亏损在2%以内
5. 定期复盘，根据市场变化调整策略
""")


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("    自选股量化分析系统")
    print("#"*60)

    analyze_portfolio()
