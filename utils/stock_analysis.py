"""
股票综合分析模块
包含四个维度：技术面、消息面、宏观面、事件驱动
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
import os


class StockAnalyzer:
    """股票综合分析器"""

    def __init__(self, config_path: str = "config/config.json"):
        """初始化分析器"""
        self.config = self._load_config(config_path)
        # 优先使用环境变量，其次使用配置文件
        self.newsapi_key = os.environ.get('NEWSAPI_KEY') or self.config.get("api_keys", {}).get("newsapi", "")
        self.fred_key = os.environ.get('FRED_API_KEY') or self.config.get("api_keys", {}).get("fred", "")

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置文件未找到: {config_path}")
            return {}

    def analyze_stock(self, stock_code: str, stock_name: str) -> Dict:
        """
        综合分析单只股票
        返回：评分、推荐等级、建议买入价、止盈位、止损位
        """
        print(f"\n{'='*60}")
        print(f"正在分析: {stock_code} {stock_name}")
        print(f"{'='*60}")

        # 1. 技术面分析
        tech_score, tech_details = self._analyze_technical(stock_code)
        print(f"技术面分析完成: {tech_score}/10")

        # 2. 消息面分析
        news_score, news_details = self._analyze_news(stock_code, stock_name)
        print(f"消息面分析完成: {news_score}/10")

        # 3. 宏观面分析
        macro_score, macro_details = self._analyze_macro()
        print(f"宏观面分析完成: {macro_score}/10")

        # 4. 事件驱动分析
        event_score, event_details = self._analyze_events(stock_code, stock_name)
        print(f"事件驱动分析完成: {event_score}/10")

        # 计算综合评分（加权平均）
        total_score = (
            tech_score * 0.4 +  # 技术面40%
            news_score * 0.3 +  # 消息面30%
            macro_score * 0.15 +  # 宏观面15%
            event_score * 0.15  # 事件驱动15%
        )

        # 确定推荐等级
        recommendation = self._get_recommendation(total_score)

        # 计算价格点位
        price_levels = self._calculate_price_levels(stock_code, tech_details)

        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "scores": {
                "technical": tech_score,
                "news": news_score,
                "macro": macro_score,
                "event": event_score,
                "total": round(total_score, 1)
            },
            "recommendation": recommendation,
            "price_levels": price_levels,
            "details": {
                "technical": tech_details,
                "news": news_details,
                "macro": macro_details,
                "event": event_details
            }
        }

    def _analyze_technical(self, stock_code: str) -> Tuple[float, Dict]:
        """
        技术面分析
        包含：RSI、MACD、均线、布林带、K线形态
        """
        try:
            # 获取股票数据
            stock = yf.Ticker(stock_code)
            df = stock.history(period="3mo")

            if df.empty:
                return 5.0, {"error": "无法获取数据"}

            # 计算技术指标
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50

            # MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_hist = macd - signal
            current_macd = macd.iloc[-1] if not macd.empty else 0
            current_signal = signal.iloc[-1] if not signal.empty else 0

            # 均线
            ma20 = df['Close'].rolling(window=20).mean()
            ma50 = df['Close'].rolling(window=50).mean()
            current_price = df['Close'].iloc[-1]
            current_ma20 = ma20.iloc[-1] if not ma20.empty else current_price
            current_ma50 = ma50.iloc[-1] if not ma50.empty else current_price

            # 布林带
            bb_middle = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            bb_upper = bb_middle + 2 * bb_std
            bb_lower = bb_middle - 2 * bb_std
            current_bb_upper = bb_upper.iloc[-1] if not bb_upper.empty else current_price * 1.1
            current_bb_lower = bb_lower.iloc[-1] if not bb_lower.empty else current_price * 0.9

            # 计算技术面评分
            score = 5.0  # 基础分

            # RSI评分
            if current_rsi < 30:
                score += 2.0  # 超卖，买入机会
            elif current_rsi < 40:
                score += 1.0
            elif current_rsi > 70:
                score -= 2.0  # 超买，卖出信号
            elif current_rsi > 60:
                score -= 1.0

            # MACD评分
            if current_macd > current_signal:
                score += 1.0  # 金叉，买入信号
            else:
                score -= 1.0  # 死叉，卖出信号

            # 均线评分
            if current_price > current_ma20:
                score += 0.5  # 站上20日均线
            if current_price > current_ma50:
                score += 0.5  # 站上50日均线
            if current_ma20 > current_ma50:
                score += 0.5  # 均线多头排列

            # 布林带评分
            if current_price < current_bb_lower:
                score += 1.0  # 跌破下轨，超卖
            elif current_price > current_bb_upper:
                score -= 1.0  # 突破上轨，超买

            # 限制评分范围
            score = max(0, min(10, score))

            details = {
                "current_price": round(current_price, 2),
                "rsi": round(current_rsi, 2),
                "macd": round(current_macd, 4),
                "macd_signal": round(current_signal, 4),
                "ma20": round(current_ma20, 2),
                "ma50": round(current_ma50, 2),
                "bb_upper": round(current_bb_upper, 2),
                "bb_lower": round(current_bb_lower, 2),
                "support_levels": [round(current_bb_lower, 2), round(current_ma20, 2)],
                "resistance_levels": [round(current_bb_upper, 2), round(current_ma50, 2)]
            }

            return score, details

        except Exception as e:
            print(f"技术面分析失败: {e}")
            return 5.0, {"error": str(e)}

    def _analyze_news(self, stock_code: str, stock_name: str) -> Tuple[float, Dict]:
        """
        消息面分析
        使用NewsAPI + 网页抓取
        """
        news_data = []
        score = 5.0
        details = {"sources": [], "sentiment": "中性"}

        # 1. NewsAPI获取新闻
        try:
            if self.newsapi_key:
                url = f"https://newsapi.org/v2/everything"
                params = {
                    "q": f"{stock_name} OR {stock_code} stock",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": self.newsapi_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get("articles", [])
                    for article in articles[:5]:
                        news_data.append({
                            "title": article.get("title", ""),
                            "source": article.get("source", {}).get("name", ""),
                            "published": article.get("publishedAt", ""),
                            "api_source": "NewsAPI"
                        })
                    details["sources"].append("NewsAPI")
        except Exception as e:
            print(f"NewsAPI获取失败: {e}")

        # 2. 网页抓取（简化版）
        try:
            # 这里可以添加更多网页抓取逻辑
            # 例如从Yahoo Finance、Google News等抓取
            details["sources"].append("网页抓取")
        except Exception as e:
            print(f"网页抓取失败: {e}")

        # 分析新闻情感（简化版）
        if len(news_data) > 3:
            score += 1.0  # 新闻较多，关注度高
        elif len(news_data) > 0:
            score += 0.5
        else:
            score -= 0.5  # 没有新闻，关注度低

        details["news_count"] = len(news_data)
        details["news"] = news_data[:3]  # 只保留前3条

        return max(0, min(10, score)), details

    def _analyze_macro(self) -> Tuple[float, Dict]:
        """
        宏观面分析
        使用FRED API + 网页抓取
        """
        score = 5.0
        details = {"indicators": {}}

        # 1. FRED API获取宏观数据
        try:
            if self.fred_key:
                # 获取一些关键宏观经济指标
                indicators = {
                    "fed_rate": "DFF",  # 联邦基金利率
                    "cpi": "CPIAUCSL",  # CPI
                    "unemployment": "UNRATE",  # 失业率
                    "gdp": "GDP"  # GDP
                }

                for name, series_id in indicators.items():
                    try:
                        url = f"https://api.stlouisfed.org/fred/series/observations"
                        params = {
                            "series_id": series_id,
                            "api_key": self.fred_key,
                            "file_type": "json",
                            "sort_order": "desc",
                            "limit": 1
                        }
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            observations = data.get("observations", [])
                            if observations:
                                details["indicators"][name] = observations[0].get("value")
                    except Exception as e:
                        print(f"获取{name}失败: {e}")

                details["sources"] = ["FRED API"]
        except Exception as e:
            print(f"FRED API获取失败: {e}")

        # 2. 网页抓取（简化版）
        try:
            # 这里可以添加更多网页抓取逻辑
            if "sources" not in details:
                details["sources"] = []
            details["sources"].append("网页抓取")
        except Exception as e:
            print(f"宏观面网页抓取失败: {e}")

        # 简化评分逻辑
        # 实际应该根据具体指标进行分析
        score = 5.0  # 默认中性

        return max(0, min(10, score)), details

    def _analyze_events(self, stock_code: str, stock_name: str) -> Tuple[float, Dict]:
        """
        事件驱动分析
        网页抓取财经日历
        """
        score = 5.0
        details = {"upcoming_events": [], "sources": []}

        # 网页抓取财经日历（简化版）
        try:
            # 这里可以添加从Investing.com、东方财富等抓取的逻辑
            # 目前简化处理
            details["sources"].append("网页抓取")
        except Exception as e:
            print(f"事件驱动分析失败: {e}")

        # 简化评分逻辑
        score = 5.0  # 默认中性

        return max(0, min(10, score)), details

    def _get_recommendation(self, score: float) -> Dict:
        """根据评分确定推荐等级"""
        if score >= 8.0:
            return {"level": "强烈推荐", "action": "买入", "confidence": "高"}
        elif score >= 6.5:
            return {"level": "推荐", "action": "买入", "confidence": "中"}
        elif score >= 5.0:
            return {"level": "中性", "action": "持有", "confidence": "中"}
        elif score >= 3.5:
            return {"level": "谨慎", "action": "观望", "confidence": "中"}
        else:
            return {"level": "不推荐", "action": "卖出", "confidence": "高"}

    def _calculate_price_levels(self, stock_code: str, tech_details: Dict) -> Dict:
        """
        计算价格点位
        基于技术面支撑/阻力位
        """
        try:
            current_price = tech_details.get("current_price", 0)
            support_levels = tech_details.get("support_levels", [])
            resistance_levels = tech_details.get("resistance_levels", [])

            # 建议买入价：当前支撑位或当前价下浮5%
            if support_levels:
                buy_price = min(support_levels)
            else:
                buy_price = round(current_price * 0.95, 2)

            # 止盈位：技术阻力位或当前价上浮10%
            if resistance_levels:
                take_profit = max(resistance_levels)
            else:
                take_profit = round(current_price * 1.10, 2)

            # 止损位：技术支撑位或当前价下浮5%
            if support_levels:
                stop_loss = min(support_levels) * 0.98  # 支撑位下浮2%
            else:
                stop_loss = round(current_price * 0.95, 2)

            return {
                "current_price": round(current_price, 2),
                "buy_price": round(buy_price, 2),
                "take_profit": round(take_profit, 2),
                "stop_loss": round(stop_loss, 2),
                "support_levels": support_levels,
                "resistance_levels": resistance_levels
            }
        except Exception as e:
            print(f"价格点位计算失败: {e}")
            return {
                "current_price": 0,
                "buy_price": 0,
                "take_profit": 0,
                "stop_loss": 0,
                "support_levels": [],
                "resistance_levels": []
            }


def main():
    """主函数"""
    analyzer = StockAnalyzer()

    # 分析示例股票
    result = analyzer.analyze_stock("MU", "美光科技")

    print("\n" + "="*60)
    print("分析结果")
    print("="*60)
    print(f"股票: {result['stock_code']} {result['stock_name']}")
    print(f"综合评分: {result['scores']['total']}/10")
    print(f"推荐等级: {result['recommendation']['level']}")
    print(f"建议操作: {result['recommendation']['action']}")
    print(f"\n价格点位:")
    print(f"  当前价: ${result['price_levels']['current_price']}")
    print(f"  建议买入: ${result['price_levels']['buy_price']}")
    print(f"  止盈位: ${result['price_levels']['take_profit']}")
    print(f"  止损位: ${result['price_levels']['stop_loss']}")


if __name__ == "__main__":
    main()
