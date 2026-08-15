"""
每日股票分析报告
使用新的四维度分析模块
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path
from utils.stock_analysis import StockAnalyzer


def send_wechat_notification(report: str):
    """
    发送企业微信通知
    """
    webhook_url = os.environ.get('WECHAT_WEBHOOK')
    if not webhook_url:
        print("未配置企业微信Webhook URL")
        return False

    # 截断过长的报告（企业微信有长度限制）
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


def format_report(results: list) -> str:
    """
    格式化分析报告
    按推荐程度排序
    """
    # 按综合评分排序（从高到低）
    sorted_results = sorted(results, key=lambda x: x['scores']['total'], reverse=True)

    report = []
    report.append("每日股票分析报告")
    report.append(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 60)
    report.append("")

    # 推荐排序部分
    report.append("【推荐排序】")
    report.append("-" * 60)

    for i, result in enumerate(sorted_results, 1):
        stock_code = result['stock_code']
        stock_name = result['stock_name']
        score = result['scores']['total']
        recommendation = result['recommendation']
        price_levels = result['price_levels']

        # 推荐等级图标
        if recommendation['level'] == '强烈推荐':
            icon = '[***]'
        elif recommendation['level'] == '推荐':
            icon = '[**]'
        elif recommendation['level'] == '中性':
            icon = '[*]'
        elif recommendation['level'] == '谨慎':
            icon = '[!]'
        else:
            icon = '[!!]'

        report.append(f"{i}. {stock_code} {stock_name} - {recommendation['level']} - 评分：{score}/10 {icon}")

        if recommendation['action'] == '买入':
            report.append(f"   建议买入：${price_levels['buy_price']}（支撑位）")
            report.append(f"   止盈位：${price_levels['take_profit']}（阻力位）")
            report.append(f"   止损位：${price_levels['stop_loss']}（支撑位）")
        else:
            report.append(f"   建议：{recommendation['action']}")

        report.append("")

    # 详细分析部分
    report.append("")
    report.append("【详细分析】")
    report.append("=" * 60)

    for result in sorted_results:
        stock_code = result['stock_code']
        stock_name = result['stock_name']
        scores = result['scores']
        details = result['details']

        report.append(f"\n【{stock_code} {stock_name}】")
        report.append(f"综合评分: {scores['total']}/10")
        report.append(f"  技术面: {scores['technical']}/10")
        report.append(f"  消息面: {scores['news']}/10")
        report.append(f"  宏观面: {scores['macro']}/10")
        report.append(f"  事件驱动: {scores['event']}/10")

        # 技术面详情
        if 'technical' in details and 'error' not in details['technical']:
            tech = details['technical']
            report.append(f"\n  技术面详情:")
            report.append(f"    当前价: ${tech.get('current_price', 'N/A')}")
            report.append(f"    RSI: {tech.get('rsi', 'N/A')}")
            report.append(f"    MACD: {tech.get('macd', 'N/A')}")
            report.append(f"    20日均线: ${tech.get('ma20', 'N/A')}")
            report.append(f"    50日均线: ${tech.get('ma50', 'N/A')}")
            report.append(f"    布林带上轨: ${tech.get('bb_upper', 'N/A')}")
            report.append(f"    布林带下轨: ${tech.get('bb_lower', 'N/A')}")

        # 价格点位
        price_levels = result['price_levels']
        report.append(f"\n  价格点位:")
        report.append(f"    当前价: ${price_levels['current_price']}")
        report.append(f"    建议买入: ${price_levels['buy_price']}")
        report.append(f"    止盈位: ${price_levels['take_profit']}")
        report.append(f"    止损位: ${price_levels['stop_loss']}")

        # 消息面详情
        if 'news' in details:
            news = details['news']
            report.append(f"\n  消息面详情:")
            report.append(f"    新闻数量: {news.get('news_count', 0)}")
            report.append(f"    数据来源: {', '.join(news.get('sources', []))}")

            if 'news' in news and news['news']:
                report.append(f"    最新新闻:")
                for item in news['news'][:2]:
                    report.append(f"      - {item.get('title', '')[:50]}...")

    report.append("")
    report.append("=" * 60)
    report.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。")
    report.append("投资有风险，入市需谨慎。")
    report.append("=" * 60)

    return "\n".join(report)


def main():
    """主函数"""
    print("开始每日股票分析...")
    print("=" * 60)

    # 初始化分析器
    analyzer = StockAnalyzer()

    # 加载股票列表
    try:
        with open("config/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
            stocks = config.get("stocks", [])
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return

    # 分析所有股票
    results = []
    for stock in stocks:
        try:
            result = analyzer.analyze_stock(stock['code'], stock['name'])
            results.append(result)
        except Exception as e:
            print(f"分析 {stock['code']} 失败: {e}")

    # 生成报告
    report = format_report(results)

    # 保存报告
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已保存: {report_file}")

    # 发送企业微信通知
    send_wechat_notification(report)


if __name__ == "__main__":
    main()
