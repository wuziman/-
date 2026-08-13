"""
每日股票分析脚本
自动分析股票并推送到企业微信
"""

import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime
import os

# ============== 配置 ==============
# 企业微信机器人Webhook URL
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f006abe3-4656-40ac-8417-9b09ab3675e5"

# 股票配置
STOCKS = [
    {'symbol': 'MU', 'folder': 'MU_美光', 'name': '美光科技'},
    {'symbol': 'SNDK', 'folder': 'SNDK_闪迪', 'name': '闪迪'},
    {'symbol': 'SOXL', 'folder': 'SOXL_半导体ETF', 'name': '三倍做多半导体ETF'},
    {'symbol': 'NKE', 'folder': 'NKE_耐克', 'name': '耐克'},
    {'symbol': 'AXTI', 'folder': 'AXT_光通信原材料', 'name': 'AXT'},
    {'symbol': 'AAOI', 'folder': 'AAOI_光模块', 'name': '祥茂光电'},
    {'symbol': 'LITE', 'folder': 'LITE_光通信器件', 'name': 'Lumentum'},
    {'symbol': 'COHR', 'folder': 'COHR_光学材料', 'name': 'Coherent'},
]

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def calculate_rsi(df, period=14):
    """计算RSI"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def analyze_stock(symbol, folder, name):
    """分析单只股票"""
    filepath = os.path.join(PROJECT_ROOT, folder, f"{symbol}_data.xlsx")

    if not os.path.exists(filepath):
        return None

    df = pd.read_excel(filepath, engine='openpyxl')
    df = df.dropna(subset=['Close'])

    if len(df) < 2:
        return None

    # 基本数据
    current = df['Close'].iloc[-1]
    prev = df['Close'].iloc[-2]
    change_pct = (current - prev) / prev * 100
    date = df['Date'].iloc[-1]

    # 计算RSI
    rsi_series = calculate_rsi(df)
    current_rsi = rsi_series.iloc[-1]

    # 判断RSI状态
    if current_rsi > 70:
        rsi_status = '超买'
    elif current_rsi < 30:
        rsi_status = '超卖'
    elif current_rsi > 50:
        rsi_status = '偏强'
    elif current_rsi > 40:
        rsi_status = '中性'
    else:
        rsi_status = '偏弱'

    # 生成建议
    if current_rsi < 35:
        suggestion = '可考虑买入'
    elif current_rsi > 65:
        suggestion = '注意风险'
    else:
        suggestion = '观望'

    return {
        'symbol': symbol,
        'name': name,
        'price': current,
        'change_pct': change_pct,
        'rsi': current_rsi,
        'rsi_status': rsi_status,
        'suggestion': suggestion,
        'date': date
    }


def format_message(results):
    """格式化消息"""
    today = datetime.now().strftime('%Y年%m月%d日')

    message = f"[每日股票分析报告]\n"
    message += f"[日期] {today}\n"
    message += "=" * 30 + "\n\n"

    for r in results:
        if r:
            change_symbol = "+" if r['change_pct'] >= 0 else ""
            message += f"[{r['name']}] {r['symbol']}\n"
            message += f"  价格: ${r['price']:.2f} {change_symbol}{r['change_pct']:.2f}%\n"
            message += f"  RSI: {r['rsi']:.1f} ({r['rsi_status']})\n"
            message += f"  建议: {r['suggestion']}\n\n"

    message += "=" * 30 + "\n"
    message += "[提示] 投资有风险，入市需谨慎\n"
    message += "[提示] 数据仅供参考，不构成投资建议"

    return message


def send_to_wechat(message):
    """发送到企业微信"""
    if "YOUR_KEY_HERE" in WECHAT_WEBHOOK:
        print("[WARNING] 请先配置企业微信Webhook URL")
        print("消息内容预览:")
        print(message)
        return False

    data = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }

    try:
        response = requests.post(WECHAT_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get('errcode') == 0:
            print("[OK] 消息发送成功！")
            return True
        else:
            print(f"[ERROR] 发送失败: {result}")
            return False
    except Exception as e:
        print(f"[ERROR] 发送失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("  每日股票分析系统")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 分析所有股票
    results = []
    for stock in STOCKS:
        print(f"分析 {stock['name']}...")
        result = analyze_stock(stock['symbol'], stock['folder'], stock['name'])
        results.append(result)

    # 生成消息
    message = format_message(results)

    # 显示消息
    print("\n" + "=" * 50)
    print("消息内容:")
    print("=" * 50)
    print(message)

    # 发送到企业微信
    print("\n" + "=" * 50)
    print("发送到企业微信...")
    send_to_wechat(message)


if __name__ == "__main__":
    main()
