"""
验证非线性策略胜率
如果买入价真的到了，胜率是多少
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def verify_winrate(stock_code, buy_price, months=6):
    """验证如果买入价到了，胜率是多少"""
    print(f"\n{'='*60}")
    print(f"验证 {stock_code} 非线性策略胜率")
    print(f"买入价: ${buy_price:.2f}")
    print(f"{'='*60}")

    # 获取历史数据
    stock = yf.Ticker(stock_code)
    data = stock.history(period="1y")

    if data.empty:
        print(f"无法获取 {stock_code} 数据")
        return None

    # 计算技术指标
    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # 布林带
    data['BB_middle'] = data['Close'].rolling(window=20).mean()
    data['BB_std'] = data['Close'].rolling(window=20).std()
    data['BB_upper'] = data['BB_middle'] + 2 * data['BB_std']
    data['BB_lower'] = data['BB_middle'] - 2 * data['BB_std']

    # 成交量比率
    data['Volume_MA20'] = data['Volume'].rolling(window=20).mean()
    data['Volume_Ratio'] = data['Volume'] / data['Volume_MA20']

    # 找到所有达到买入价的日期
    buy_dates = data[data['Close'] <= buy_price].index

    if len(buy_dates) == 0:
        print(f"过去{months}个月内没有达到买入价 ${buy_price:.2f}")
        print(f"当前价: ${data['Close'].iloc[-1]:.2f}")
        print(f"距离买入价: {(data['Close'].iloc[-1] - buy_price) / buy_price * 100:.2f}%")
        return None

    print(f"\n过去{months}个月内达到买入价的次数: {len(buy_dates)}")

    # 计算每次买入后的收益
    wins = 0
    losses = 0
    total_return = 0

    for buy_date in buy_dates:
        buy_idx = data.index.get_loc(buy_date)
        buy_price_actual = data['Close'].iloc[buy_idx]

        # 计算买入后30天的收益
        if buy_idx + 30 < len(data):
            sell_price = data['Close'].iloc[buy_idx + 30]
            profit = (sell_price - buy_price_actual) / buy_price_actual * 100
            total_return += profit

            if profit > 0:
                wins += 1
                print(f"  买入日期: {buy_date.strftime('%Y-%m-%d')}, 买入价: ${buy_price_actual:.2f}, 30天后: ${sell_price:.2f}, 盈利: {profit:.2f}%")
            else:
                losses += 1
                print(f"  买入日期: {buy_date.strftime('%Y-%m-%d')}, 买入价: ${buy_price_actual:.2f}, 30天后: ${sell_price:.2f}, 亏损: {profit:.2f}%")

    total_trades = wins + losses
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    avg_return = total_return / total_trades if total_trades > 0 else 0

    print(f"\n【胜率统计】")
    print(f"总交易次数: {total_trades}")
    print(f"盈利次数: {wins}")
    print(f"亏损次数: {losses}")
    print(f"胜率: {win_rate:.2f}%")
    print(f"平均收益: {avg_return:.2f}%")

    return {
        'stock_code': stock_code,
        'buy_price': buy_price,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'avg_return': avg_return
    }


def main():
    """主函数"""
    print("验证非线性策略胜率")
    print("=" * 60)

    # 非线性策略的买入价
    nonlinear_points = {
        'MU': 890.05,
        'SOXL': 133.32,
        'COHR': 303.75,
        'NKE': 42.00,
        'AXTI': 62.25,
        'LITE': 797.99,
        'SNDK': 1353.55
    }

    results = []
    for stock, buy_price in nonlinear_points.items():
        try:
            result = verify_winrate(stock, buy_price)
            if result:
                results.append(result)
        except Exception as e:
            print(f"验证 {stock} 失败: {e}")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总结果")
    print(f"{'='*60}")

    print(f"\n{'股票':<8} {'买入价':<10} {'交易次数':<10} {'胜率':<10} {'平均收益':<10}")
    print("-" * 50)

    for result in results:
        print(f"{result['stock_code']:<8} ${result['buy_price']:<9.2f} {result['total_trades']:<10} {result['win_rate']:<9.2f}% {result['avg_return']:<9.2f}%")

    # 计算平均胜率
    if results:
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
        avg_return = sum(r['avg_return'] for r in results) / len(results)
        print(f"\n平均胜率: {avg_win_rate:.2f}%")
        print(f"平均收益: {avg_return:.2f}%")


if __name__ == "__main__":
    main()
