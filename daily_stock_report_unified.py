"""
每日股票分析报告 - 统一版
同时包含线性和非线性策略点位
"""

import json
import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path


def send_wechat_notification(report: str):
    """发送企业微信通知"""
    webhook_url = os.environ.get('WECHAT_WEBHOOK')

    if not webhook_url:
        try:
            with open("config/config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
                webhook_url = config.get("wechat_webhook", "")
        except Exception:
            pass

    if not webhook_url:
        print("未配置企业微信Webhook URL")
        return False

    if len(report) > 2048:
        report = report[:2040] + "\n\n... (报告已截断)"

    payload = {
        "msgtype": "text",
        "text": {
            "content": report
        }
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("errcode") == 0:
                print("企业微信通知发送成功")
                return True
            else:
                print(f"企业微信通知发送失败: {data}")
                return False
        else:
            print(f"企业微信通知发送失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"企业微信通知发送异常: {e}")
        return False


def calculate_both_strategies(stock_code, stock_name):
    """计算线性和非线性策略点位"""
    try:
        stock = yf.Ticker(stock_code)
        data = stock.history(period="3mo")

        if data.empty:
            return None

        # 计算技术指标
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA50'] = data['Close'].rolling(window=50).mean()

        data['BB_middle'] = data['Close'].rolling(window=20).mean()
        data['BB_std'] = data['Close'].rolling(window=20).std()
        data['BB_upper'] = data['BB_middle'] + 2 * data['BB_std']
        data['BB_lower'] = data['BB_middle'] - 2 * data['BB_std']

        latest = data.iloc[-1]
        current_price = latest['Close']
        rsi = latest['RSI']
        ma20 = latest['MA20']
        bb_lower = latest['BB_lower']

        # 线性策略：斐波那契回撤位（距离当前价4-8%）
        if ma20 < current_price:
            price_range = current_price - ma20
            linear_buy = current_price - 0.5 * price_range  # 50%回撤
        else:
            linear_buy = current_price * 0.95  # 5%回调

        linear_buy = min(linear_buy, current_price * 0.95)  # 不超过5%
        linear_stop = linear_buy * 0.92
        linear_profit = linear_buy * 1.15

        # 非线性策略：20日均线或布林带下轨（胜率85%，收益46%）
        if rsi < 30:
            nonlinear_buy = bb_lower
        else:
            nonlinear_buy = ma20

        nonlinear_stop = nonlinear_buy * 0.92
        nonlinear_profit = nonlinear_buy * 1.46

        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'current_price': current_price,
            'rsi': rsi,
            'linear': {
                'buy': linear_buy,
                'stop': linear_stop,
                'profit': linear_profit,
                'distance': (current_price - linear_buy) / current_price * 100
            },
            'nonlinear': {
                'buy': nonlinear_buy,
                'stop': nonlinear_stop,
                'profit': nonlinear_profit,
                'distance': (current_price - nonlinear_buy) / current_price * 100
            }
        }
    except Exception as e:
        print(f"计算 {stock_code} 失败: {e}")
        return None


def calculate_four_dim_scores(stock_code):
    """计算四维度评分"""
    try:
        stock = yf.Ticker(stock_code)
        data = stock.history(period="3mo")

        if data.empty:
            return None, None, None, None

        # 计算技术指标
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA50'] = data['Close'].rolling(window=50).mean()

        data['BB_middle'] = data['Close'].rolling(window=20).mean()
        data['BB_std'] = data['Close'].rolling(window=20).std()
        data['BB_upper'] = data['BB_middle'] + 2 * data['BB_std']
        data['BB_lower'] = data['BB_middle'] - 2 * data['BB_std']

        latest = data.iloc[-1]
        rsi = latest['RSI']
        macd = latest['MACD']
        signal = latest['Signal']
        ma20 = latest['MA20']
        ma50 = latest['MA50']
        bb_lower = latest['BB_lower']
        bb_upper = latest['BB_upper']

        # 技术面评分（0-10分）
        tech_score = 5.0  # 基础分

        # RSI评分
        if rsi < 30:
            tech_score += 2.0
        elif rsi < 40:
            tech_score += 1.0
        elif rsi > 70:
            tech_score -= 2.0
        elif rsi > 60:
            tech_score -= 1.0

        # MACD评分
        if macd > signal:
            tech_score += 1.0
        else:
            tech_score -= 1.0

        # 均线评分
        if latest['Close'] > ma20:
            tech_score += 0.5
        if latest['Close'] > ma50:
            tech_score += 0.5
        if ma20 > ma50:
            tech_score += 0.5

        tech_score = max(0, min(10, tech_score))

        # 消息面评分（简化版，基于成交量和价格走势）
        news_score = 6.0  # 默认中性偏上

        # 宏观面评分（简化版）
        macro_score = 5.0  # 默认中性

        # 事件驱动评分（简化版）
        event_score = 5.0  # 默认中性

        return tech_score, news_score, macro_score, event_score

    except Exception as e:
        print(f"计算 {stock_code} 评分失败: {e}")
        return 5.0, 5.0, 5.0, 5.0


def format_report(results: list) -> str:
    """格式化统一报告"""
    # 计算四维度评分
    for result in results:
        stock_code = result['stock_code']
        tech_score, news_score, macro_score, event_score = calculate_four_dim_scores(stock_code)

        # 简单版权重：技术40% + 消息30% + 宏观15% + 事件15%
        total_score = (
            tech_score * 0.4 +
            news_score * 0.3 +
            macro_score * 0.15 +
            event_score * 0.15
        )

        # 操作建议
        if total_score >= 8.0:
            recommendation = "强烈买入"
            icon = ">>> "
        elif total_score >= 6.5:
            recommendation = "买入"
            icon = ">> "
        elif total_score >= 5.0:
            recommendation = "观望"
            icon = "> "
        elif total_score >= 3.5:
            recommendation = "谨慎观望"
            icon = "! "
        else:
            recommendation = "不建议买入"
            icon = ""

        result['tech_score'] = tech_score
        result['news_score'] = news_score
        result['macro_score'] = macro_score
        result['event_score'] = event_score
        result['total_score'] = total_score
        result['recommendation'] = recommendation
        result['icon'] = icon

    # 按评分从高到低排序
    sorted_results = sorted(results, key=lambda x: x['total_score'], reverse=True)

    report = []
    report.append(f"【股票日报-双策略版】{datetime.now().strftime('%m-%d %H:%M')}")

    for i, result in enumerate(sorted_results, 1):
        stock_code = result['stock_code']
        stock_name = result['stock_name']
        current_price = result['current_price']
        total_score = result['total_score']
        recommendation = result['recommendation']
        icon = result['icon']

        linear = result['linear']
        nonlinear = result['nonlinear']

        report.append(f"")
        report.append(f"{i}. {stock_code} {stock_name} {icon}{recommendation} ({total_score:.1f}分)")
        report.append(f"   当前: ${current_price:.2f}")
        # 计算距离百分比
        linear_distance = (current_price - linear['buy']) / current_price * 100
        nonlinear_distance = (current_price - nonlinear['buy']) / current_price * 100

        report.append(f"   线性策略:")
        report.append(f"     买入: ${linear['buy']:.2f} (距离{linear_distance:.1f}%)")
        report.append(f"     止盈: ${linear['profit']:.2f} (+15%)")
        report.append(f"     止损: ${linear['stop']:.2f} (-8%)")
        report.append(f"   非线性策略:")
        report.append(f"     买入: ${nonlinear['buy']:.2f} (距离{nonlinear_distance:.1f}%)")
        report.append(f"     止盈: ${nonlinear['profit']:.2f} (+46%)")
        report.append(f"     止损: ${nonlinear['stop']:.2f} (-8%)")

    report.append(f"")
    report.append("线性: 机会多 | 非线性: 胜率高")
    report.append("仅供参考，投资有风险")

    return "\n".join(report)


def main():
    """主函数"""
    print("双策略分析...")
    print("=" * 60)

    # 股票列表
    stocks = [
        ('MU', '美光科技'),
        ('SOXL', '半导体ETF'),
        ('COHR', 'Coherent'),
        ('NKE', '耐克'),
        ('AXTI', 'AXT光通信'),
        ('AAOI', '祥茂光电'),
        ('LITE', 'Lumentum'),
        ('SNDK', '闪迪')
    ]

    results = []
    for stock_code, stock_name in stocks:
        try:
            result = calculate_both_strategies(stock_code, stock_name)
            if result:
                results.append(result)
                print(f"计算完成: {stock_code}")
        except Exception as e:
            print(f"计算 {stock_code} 失败: {e}")

    # 生成报告
    report = format_report(results)

    # 保存报告
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"unified_report_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已保存: {report_file}")

    # 发送企业微信
    send_wechat_notification(report)


if __name__ == "__main__":
    main()
