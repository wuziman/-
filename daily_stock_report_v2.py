"""
每日股票分析报告 - 研究验证版（方案1）
使用学术研究验证的多因子权重
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

    # 如果环境变量中没有，从config.json读取
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
    格式化分析报告（研究验证版）
    使用学术研究验证的多因子权重
    """
    # 按综合评分排序（从高到低）
    sorted_results = sorted(results, key=lambda x: x['scores']['total'], reverse=True)

    report = []
    report.append(f"【股票日报-研究验证版】{datetime.now().strftime('%m-%d %H:%M')}")
    report.append("=" * 40)

    for i, result in enumerate(sorted_results, 1):
        stock_code = result['stock_code']
        stock_name = result['stock_name']
        score = result['scores']['total']
        recommendation = result['recommendation']
        price_levels = result['price_levels']
        factor_scores = result.get('factor_scores', {})

        # 推荐等级图标
        if recommendation['level'] == '强烈推荐':
            icon = '>>>'
        elif recommendation['level'] == '推荐':
            icon = '>>'
        elif recommendation['level'] == '中性':
            icon = '>'
        elif recommendation['level'] == '谨慎':
            icon = '!'
        else:
            icon = '!!'

        report.append(f"{i}. {stock_code} {score}分 [{recommendation['action']}] {icon}")
        report.append(f"   当前: ${price_levels['current_price']}")
        report.append(f"   买入: ${price_levels['buy_price']}")
        report.append(f"   止盈: ${price_levels['take_profit']}")
        report.append(f"   止损: ${price_levels['stop_loss']}")

        # 显示因子得分
        if factor_scores:
            tech = factor_scores.get('technical', 0)
            news = factor_scores.get('news', 0)
            macro = factor_scores.get('macro', 0)
            event = factor_scores.get('event', 0)
            report.append(f"   因子: 技{tech} 新{news} 宏{macro} 事{event}")

        report.append("")

    report.append("=" * 40)
    report.append("权重: 技术35% + 消息15% + 宏观25% + 事件25%")
    report.append("仅供参考，投资有风险")

    return "\n".join(report)


def main():
    """主函数"""
    print("开始每日股票分析（研究验证版）...")
    print("=" * 60)

    # 初始化分析器
    analyzer = StockAnalyzer()

    # 加载股票列表
    try:
        with open("config/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
            stocks = config.get("stocks", [])
    except Exception as e:
        print(f"加载配置失败: {e}")
        return

    # 分析所有股票（使用研究验证版模式）
    results = []
    for stock in stocks:
        try:
            result = analyzer.analyze_stock(stock['code'], stock['name'], mode="research")
            results.append(result)
        except Exception as e:
            print(f"分析 {stock['code']} 失败: {e}")

    # 生成报告
    report = format_report(results)

    # 保存报告
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"daily_report_v2_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已保存: {report_file}")

    # 发送企业微信通知
    send_wechat_notification(report)


if __name__ == "__main__":
    main()
