"""
非线性策略点位计算
使用决策树规则计算买入点位
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


def calculate_nonlinear_points(stock_code):
    """计算非线性策略的买入点位"""
    print(f"\n{'='*60}")
    print(f"计算 {stock_code} 非线性策略点位")
    print(f"{'='*60}")

    # 获取历史数据
    stock = yf.Ticker(stock_code)
    data = stock.history(period="3mo")

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

    # 均线
    data['MA20'] = data['Close'].rolling(window=20).mean()
    data['MA50'] = data['Close'].rolling(window=50).mean()

    # 布林带
    data['BB_middle'] = data['Close'].rolling(window=20).mean()
    data['BB_std'] = data['Close'].rolling(window=20).std()
    data['BB_upper'] = data['BB_middle'] + 2 * data['BB_std']
    data['BB_lower'] = data['BB_middle'] - 2 * data['BB_std']

    # 成交量比率
    data['Volume_MA20'] = data['Volume'].rolling(window=20).mean()
    data['Volume_Ratio'] = data['Volume'] / data['Volume_MA20']

    # 获取最新数据
    latest = data.iloc[-1]
    current_price = latest['Close']
    rsi = latest['RSI']
    macd = latest['MACD']
    signal = latest['Signal']
    ma20 = latest['MA20']
    ma50 = latest['MA50']
    bb_upper = latest['BB_upper']
    bb_lower = latest['BB_lower']
    volume_ratio = latest['Volume_Ratio']

    print(f"\n当前数据:")
    print(f"  当前价: ${current_price:.2f}")
    print(f"  RSI: {rsi:.2f}")
    print(f"  MACD: {macd:.4f}")
    print(f"  信号线: {signal:.4f}")
    print(f"  20日均线: ${ma20:.2f}")
    print(f"  50日均线: ${ma50:.2f}")
    print(f"  布林带上轨: ${bb_upper:.2f}")
    print(f"  布林带下轨: ${bb_lower:.2f}")
    print(f"  成交量比率: {volume_ratio:.2f}")

    # 非线性策略规则
    print(f"\n【非线性策略规则】")

    rules = []

    # 规则1：RSI超卖 + MACD金叉 = 强买入
    if rsi < 30 and macd > signal:
        rules.append({
            'name': '规则1: RSI超卖 + MACD金叉',
            'signal': '强买入',
            'buy_price': current_price,
            'confidence': 90
        })
        print(f"  ✅ 触发: RSI({rsi:.2f}) < 30 且 MACD > 信号线")

    # 规则2：RSI超卖 + 价格跌破布林带下轨 = 买入
    if rsi < 30 and current_price < bb_lower:
        rules.append({
            'name': '规则2: RSI超卖 + 跌破布林带下轨',
            'signal': '买入',
            'buy_price': current_price,
            'confidence': 80
        })
        print(f"  ✅ 触发: RSI({rsi:.2f}) < 30 且 价格 < 布林带下轨")

    # 规则3：MACD金叉 + 成交量放大 = 买入
    if macd > signal and volume_ratio > 1.5:
        rules.append({
            'name': '规则3: MACD金叉 + 成交量放大',
            'signal': '买入',
            'buy_price': current_price,
            'confidence': 70
        })
        print(f"  ✅ 触发: MACD > 信号线 且 成交量比率 > 1.5")

    # 规则4：价格在20日均线附近 + RSI中性 = 买入
    if abs(current_price - ma20) / ma20 < 0.02 and 40 < rsi < 60:
        buy_price = ma20
        rules.append({
            'name': '规则4: 价格在20日均线附近 + RSI中性',
            'signal': '买入',
            'buy_price': buy_price,
            'confidence': 60
        })
        print(f"  ✅ 触发: 价格在20日均线附近且RSI中性")

    # 规则5：价格跌破布林带下轨 + 成交量放大 = 买入
    if current_price < bb_lower and volume_ratio > 1.5:
        buy_price = bb_lower
        rules.append({
            'name': '规则5: 跌破布林带下轨 + 成交量放大',
            'signal': '买入',
            'buy_price': buy_price,
            'confidence': 65
        })
        print(f"  ✅ 触发: 价格 < 布林带下轨 且 成交量放大")

    # 如果没有触发任何规则，使用默认规则
    if not rules:
        # 默认规则：价格回调到20日均线附近
        buy_price = ma20
        rules.append({
            'name': '默认规则: 价格回调到20日均线',
            'signal': '观望买入',
            'buy_price': buy_price,
            'confidence': 50
        })
        print(f"  无特殊规则触发，使用默认规则")

    # 计算止损止盈
    print(f"\n【非线性策略点位】")

    results = []
    for rule in rules:
        buy_price = rule['buy_price']

        # 止损：买入价 - 8%
        stop_loss = buy_price * 0.92

        # 止盈：买入价 + 15%
        take_profit = buy_price * 1.15

        result = {
            'stock_code': stock_code,
            'current_price': current_price,
            'rule': rule['name'],
            'signal': rule['signal'],
            'buy_price': buy_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'confidence': rule['confidence'],
            'risk_reward': (take_profit - buy_price) / (buy_price - stop_loss)
        }
        results.append(result)

        print(f"\n{rule['name']}:")
        print(f"  信号: {rule['signal']}")
        print(f"  买入价: ${buy_price:.2f}")
        print(f"  止损价: ${stop_loss:.2f} (-8%)")
        print(f"  止盈价: ${take_profit:.2f} (+15%)")
        print(f"  信心度: {rule['confidence']}%")
        print(f"  风险回报比: {result['risk_reward']:.2f}")

    return results


def main():
    """主函数"""
    print("非线性策略点位计算")
    print("=" * 60)

    # 计算每只股票的点位
    stocks = ['MU', 'SOXL', 'COHR', 'NKE', 'AXTI', 'AAOI', 'LITE', 'SNDK']

    all_results = []
    for stock in stocks:
        try:
            results = calculate_nonlinear_points(stock)
            if results:
                all_results.extend(results)
        except Exception as e:
            print(f"计算 {stock} 失败: {e}")

    # 汇总报告
    print(f"\n{'='*60}")
    print("非线性策略点位汇总")
    print(f"{'='*60}")

    print(f"\n{'股票':<8} {'当前价':<10} {'买入价':<10} {'止损价':<10} {'止盈价':<10} {'信心度':<8}")
    print("-" * 60)

    for result in all_results:
        print(f"{result['stock_code']:<8} ${result['current_price']:<9.2f} ${result['buy_price']:<9.2f} ${result['stop_loss']:<9.2f} ${result['take_profit']:<9.2f} {result['confidence']:<7}%")


if __name__ == "__main__":
    main()
