"""
分析服务
真实数据源：
- 消息面：NewsAPI（美股）+ 新浪个股新闻（A股），关键词情感分析
- 宏观面：FRED API（联邦利率/CPI/失业率），规则评分
- 事件驱动：yfinance财报日历（美股）
"""

import re
import json
import logging
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests
from typing import Dict, Tuple, Any, List
from .stock_service import StockService, _get_cn_session
from .tech_score import calculate_tech_score
from ..utils.indicators import calculate_all_indicators

logger = logging.getLogger(__name__)


# ============================================
# 情感分析关键词库
# ============================================
POSITIVE_CN = [
    '利好', '上涨', '增长', '超预期', '突破', '新高', '回购', '分红', '中标',
    '签约', '获准', '盈利', '大涨', '涨停', '走强', '增持', '买入评级', '推荐',
    '达成合作', '订单', '扩产', '获批', '回暖', '复苏', '领跑', '居前', '看好',
]
NEGATIVE_CN = [
    '利空', '下跌', '下滑', '亏损', '暴跌', '跌停', '减持', '卖出评级', '调查',
    '处罚', '违规', '诉讼', '警告', '风险提示', '退市', '质押', '冻结', '裁员',
    '召回', '纠纷', '内耗', '退潮', '裸泳', '卡脖子', '连亏', '承压', '遇冷',
]
POSITIVE_EN = [
    'beat', 'surge', 'rally', 'record high', 'upgrade', 'buy rating', 'growth',
    'profit', 'gain', 'bullish', 'outperform', 'partnership', 'contract',
    'dividend', 'buyback', 'expansion', 'strong', 'soar', 'jump', 'top estimates',
]
NEGATIVE_EN = [
    'miss', 'plunge', 'slump', 'downgrade', 'sell rating', 'loss', 'decline',
    'bearish', 'underperform', 'lawsuit', 'probe', 'recall', 'layoff',
    'warning', 'fraud', 'weak', 'fall', 'drop', 'cut', 'shortfall',
]


def score_text_sentiment(text: str) -> int:
    """
    对单条文本做关键词情感打分

    返回：1（利好）/ 0（中性）/ -1（利空）
    """
    text_lower = text.lower()
    pos = sum(1 for kw in POSITIVE_CN if kw in text) + \
          sum(1 for kw in POSITIVE_EN if kw in text_lower)
    neg = sum(1 for kw in NEGATIVE_CN if kw in text) + \
          sum(1 for kw in NEGATIVE_EN if kw in text_lower)
    if pos > neg:
        return 1
    if neg > pos:
        return -1
    return 0


def _load_api_keys() -> Dict[str, str]:
    """加载API keys：环境变量优先，其次原项目config/config.json"""
    keys = {
        'newsapi': os.environ.get('NEWSAPI_KEY', ''),
        'fred': os.environ.get('FRED_API_KEY', ''),
    }
    if not (keys['newsapi'] and keys['fred']):
        # stock-platform/backend/app/services/analysis_service.py → parents[4] = 股票投资/
        try:
            config_path = Path(__file__).resolve().parents[4] / 'config' / 'config.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                api = cfg.get('api_keys', {})
                keys['newsapi'] = keys['newsapi'] or api.get('newsapi', '')
                keys['fred'] = keys['fred'] or api.get('fred', '')
        except Exception:
            pass
    return keys


class AnalysisService:
    """股票分析服务"""

    def __init__(self):
        self.stock_service = StockService()
        self.api_keys = _load_api_keys()

    def analyze_stock(self, stock_code: str, stock_name: str, market: str = "US", mode: str = "simple") -> Dict:
        """
        综合分析单只股票
        """
        print(f"正在分析: {stock_code} {stock_name} [{market}]")

        # 获取股票数据
        df = self.stock_service.get_stock_data(stock_code, market)
        if df is None or df.empty:
            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'error': '无法获取数据'
            }

        # 计算技术指标
        df_with_indicators = calculate_all_indicators(df)
        latest = df_with_indicators.iloc[-1]

        # 技术面：纯本地指标计算，无需并行
        tech_score, tech_details = self._analyze_technical(df_with_indicators, latest)

        # 消息面/宏观面/事件驱动互不依赖，三路并行拉取（各自有独立超时）
        with ThreadPoolExecutor(max_workers=4) as executor:
            fut_news = executor.submit(self._analyze_news, stock_code, stock_name, market)
            fut_macro = executor.submit(self._analyze_macro, market)
            fut_event = executor.submit(self._analyze_events, stock_code, stock_name, market)
            news_score, news_details = fut_news.result()
            macro_score, macro_details = fut_macro.result()
            event_score, event_details = fut_event.result()

        # 计算综合评分
        if mode == "research":
            total_score = (
                tech_score * 0.35 +
                news_score * 0.15 +
                macro_score * 0.25 +
                event_score * 0.25
            )
        else:
            total_score = (
                tech_score * 0.4 +
                news_score * 0.3 +
                macro_score * 0.15 +
                event_score * 0.15
            )

        # 确定推荐等级
        recommendation = self._get_recommendation(total_score)

        # 计算三策略点位（线性/非线性/MACD）
        price_levels = self._calculate_both_strategies(df_with_indicators, latest, market)

        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'market': market,
            'scores': {
                'technical': round(tech_score, 1),
                'news': round(news_score, 1),
                'macro': round(macro_score, 1),
                'event': round(event_score, 1),
                'total': round(total_score, 1)
            },
            'recommendation': recommendation,
            'price_levels': price_levels,
            'details': {
                'technical': tech_details,
                'news': news_details,
                'macro': macro_details,
                'event': event_details
            }
        }

    # ============================================
    # 1. 技术面
    # ============================================
    def _analyze_technical(self, df: pd.DataFrame, latest: pd.Series) -> Tuple[float, Dict]:
        """技术面分析（评分规则在 tech_score.calculate_tech_score，与report_service共用）"""
        return calculate_tech_score(latest)

    # ============================================
    # 2. 消息面（真实新闻 + 情感分析）
    # ============================================
    def _analyze_news(self, stock_code: str, stock_name: str, market: str = "US") -> Tuple[float, Dict]:
        """消息面分析：真实新闻获取 + 关键词情感评分"""
        news_items: List[Dict] = []

        try:
            if market == "US":
                news_items = self._fetch_news_us(stock_code, stock_name)
            else:
                news_items = self._fetch_news_cn(stock_code)
        except Exception as e:
            print(f"新闻获取失败: {e}")

        # 情感统计
        pos_count = sum(1 for n in news_items if n['sentiment'] > 0)
        neg_count = sum(1 for n in news_items if n['sentiment'] < 0)
        net_sentiment = pos_count - neg_count

        # 评分：基础5分 + 关注度 + 情感倾向
        score = 5.0
        if len(news_items) >= 5:
            score += 0.5  # 新闻多，关注度高
        elif len(news_items) == 0:
            score -= 1.0  # 无新闻，关注度低

        # 每条利好+0.3 / 利空-0.3，总影响限±2
        score += max(-2.0, min(2.0, net_sentiment * 0.3))

        # 情感标签
        if score >= 6.5:
            sentiment_label = '偏多'
        elif score >= 5.5:
            sentiment_label = '中性偏多'
        elif score >= 4.5:
            sentiment_label = '中性'
        elif score >= 3.5:
            sentiment_label = '中性偏空'
        else:
            sentiment_label = '偏空'

        details = {
            'news_count': len(news_items),
            'positive_count': pos_count,
            'negative_count': neg_count,
            'sentiment': sentiment_label,
            'sources': ['NewsAPI'] if market == 'US' else ['新浪财经'],
            'news': news_items[:20]  # 前端默认显示8条，可展开全部
        }

        return max(0, min(10, score)), details

    def _fetch_news_us(self, stock_code: str, stock_name: str) -> List[Dict]:
        """美股新闻：NewsAPI"""
        items: List[Dict] = []
        api_key = self.api_keys.get('newsapi')
        if not api_key:
            return items

        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    # 引号短语匹配，避免代码缩写(如MU)误匹配无关新闻
                    'q': f'"{stock_name}"',
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 15,
                    'apiKey': api_key
                },
                timeout=8
            )
            if resp.status_code == 200:
                for art in resp.json().get('articles', [])[:15]:
                    title = art.get('title') or ''
                    if not title:
                        continue
                    items.append({
                        'title': title,
                        'source': (art.get('source') or {}).get('name', ''),
                        'date': (art.get('publishedAt') or '')[:10],
                        'url': art.get('url') or '',
                        'sentiment': score_text_sentiment(title)
                    })
        except Exception as e:
            print(f"NewsAPI获取失败: {e}")

        return items

    def _fetch_news_cn(self, stock_code: str) -> List[Dict]:
        """A股新闻：新浪个股新闻页（直连不走代理）"""
        items: List[Dict] = []

        code = stock_code.replace('.SH', '').replace('.SZ', '')
        if len(code) != 6 or not code.isdigit():
            return items

        prefix = 'sh' if code.startswith('6') else 'sz'
        url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{prefix}{code}.phtml"

        try:
            session = _get_cn_session()
            resp = session.get(url, timeout=8)
            resp.encoding = 'gbk'

            # 解析格式：&nbsp;日期&nbsp;时间&nbsp;<a href='..'>标题</a>
            # 注意：HTML源码中是字面量"&nbsp;"实体，不是空白字符
            sep = r"(?:\s|&nbsp;|#xa0;|\xa0)*"
            pattern = re.compile(
                rf"(\d{{4}}-\d{{2}}-\d{{2}}){sep}(\d{{2}}:\d{{2}}){sep}<a[^>]*href='([^']+)'[^>]*>([^<]+)</a>"
            )
            for m in pattern.finditer(resp.text):
                date_str, time_str, href, title = m.groups()
                # 新浪链接多为绝对地址；兼容协议相对(//)与根相对(/)写法
                if href.startswith('//'):
                    link = 'https:' + href
                elif href.startswith('http'):
                    link = href
                else:
                    link = 'https://vip.stock.finance.sina.com.cn' + href
                items.append({
                    'title': title.strip(),
                    'source': '新浪财经',
                    'date': f"{date_str} {time_str}",
                    'url': link,
                    'sentiment': score_text_sentiment(title)
                })
                if len(items) >= 20:
                    break
        except Exception as e:
            print(f"新浪新闻获取失败: {e}")

        return items

    # ============================================
    # 3. 宏观面（FRED真实数据 + 规则评分）
    # ============================================
    def _analyze_macro(self, market: str = "US") -> Tuple[float, Dict]:
        """宏观面分析：FRED利率/CPI/失业率"""
        score = 5.0
        details: Dict[str, Any] = {
            'indicators': {},
            'interpretations': [],
            'sources': []
        }

        fred_key = self.api_keys.get('fred')
        if not fred_key:
            details['interpretations'].append('未配置FRED API Key，使用中性评分')
            return score, details

        # 获取：联邦利率（近3个月）、CPI（近25个月，过滤'.'后取13个算同比）、失业率
        fed_rates = self._fred_series('DFF', months=4)
        cpi_series = self._fred_series('CPIAUCSL', months=25)
        unrate = self._fred_series('UNRATE', months=1)

        if not fed_rates and not cpi_series and not unrate:
            details['interpretations'].append('FRED数据获取失败，使用中性评分')
            return score, details

        details['sources'].append('FRED')

        # 1. 联邦基金利率趋势：降息利好股市
        if len(fed_rates) >= 2:
            latest_rate = fed_rates[-1]['value']
            month_ago_rate = fed_rates[0]['value']
            details['indicators']['fed_rate'] = latest_rate
            if latest_rate < month_ago_rate - 0.05:
                score += 0.5
                details['interpretations'].append(f"利率下行({month_ago_rate}%→{latest_rate}%)，流动性宽松利好")
            elif latest_rate > month_ago_rate + 0.05:
                score -= 0.5
                details['interpretations'].append(f"利率上行({month_ago_rate}%→{latest_rate}%)，流动性收紧利空")
            else:
                details['interpretations'].append(f"利率平稳({latest_rate}%)")

        # 2. CPI同比：通胀温和利好，高通胀利空
        #    （FRED近期月份可能为'.'占位，多取一些再过滤）
        if len(cpi_series) >= 13:
            cpi_latest = cpi_series[-1]['value']
            cpi_year_ago = cpi_series[-13]['value']  # 12个月前
            if cpi_year_ago and cpi_latest:
                cpi_yoy = (cpi_latest / cpi_year_ago - 1) * 100
                details['indicators']['cpi_yoy'] = round(cpi_yoy, 2)
                if cpi_yoy < 3:
                    score += 0.5
                    details['interpretations'].append(f"通胀温和(CPI同比{cpi_yoy:.1f}%)")
                elif cpi_yoy > 4:
                    score -= 0.5
                    details['interpretations'].append(f"通胀偏高(CPI同比{cpi_yoy:.1f}%)")
                else:
                    details['interpretations'].append(f"通胀中性(CPI同比{cpi_yoy:.1f}%)")

        # 3. 失业率：就业强劲利好
        if unrate:
            latest_unrate = unrate[-1]['value']
            details['indicators']['unemployment'] = latest_unrate
            if latest_unrate and latest_unrate < 4.5:
                score += 0.5
                details['interpretations'].append(f"就业强劲(失业率{latest_unrate}%)")
            elif latest_unrate and latest_unrate > 5.5:
                score -= 0.5
                details['interpretations'].append(f"就业走弱(失业率{latest_unrate}%)")
            else:
                details['interpretations'].append(f"就业平稳(失业率{latest_unrate}%)")

        return max(0, min(10, score)), details

    def _fred_series(self, series_id: str, months: int = 1) -> List[Dict]:
        """获取FRED序列最近N个月数据，失败返回空列表"""
        try:
            resp = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    'series_id': series_id,
                    'api_key': self.api_keys['fred'],
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': months
                },
                timeout=8
            )
            if resp.status_code == 200:
                obs = resp.json().get('observations', [])
                result = []
                for o in reversed(obs):  # 时间正序
                    val = o.get('value')
                    if val not in (None, '.', ''):
                        result.append({'date': o.get('date'), 'value': float(val)})
                return result
        except Exception as e:
            print(f"FRED {series_id} 获取失败: {e}")
        return []

    # ============================================
    # 4. 事件驱动（财报日历）
    # ============================================
    def _analyze_events(self, stock_code: str, stock_name: str, market: str = "US") -> Tuple[float, Dict]:
        """事件驱动分析：财报日历（美股），A股暂用中性"""
        score = 5.0
        details: Dict[str, Any] = {'events': [], 'sources': []}

        if market == "US":
            try:
                import yfinance as yf
                cal = yf.Ticker(stock_code).calendar
                earnings_dates = None
                if isinstance(cal, dict):
                    earnings_dates = cal.get('Earnings Date')
                elif cal is not None and hasattr(cal, 'loc'):
                    try:
                        earnings_dates = cal.loc['Earnings Date']
                    except KeyError:
                        pass

                if earnings_dates:
                    if isinstance(earnings_dates, (list, pd.DatetimeIndex)):
                        next_date = earnings_dates[0]
                    else:
                        next_date = earnings_dates

                    if hasattr(next_date, 'date'):
                        date_str = next_date.date().isoformat()
                    else:
                        date_str = str(next_date)

                    details['sources'].append('yfinance')
                    days_away = (pd.Timestamp(next_date) - pd.Timestamp.now()).days
                    details['events'].append({
                        'name': '财报发布',
                        'date': date_str,
                        'days_away': days_away,
                        'impact': '财报临近，波动可能加大'
                    })
                    # 财报前7天内：机会与风险并存，轻微降分提醒谨慎
                    if 0 <= days_away <= 7:
                        score -= 0.5
                        details['events'][-1]['impact'] = '⚠️ 财报临近（7天内），业绩不确定性高，注意波动风险'
            except Exception as e:
                print(f"财报日历获取失败: {e}")
        else:
            details['events'].append({
                'name': 'A股事件跟踪',
                'date': '',
                'days_away': None,
                'impact': 'A股财报/事件日历暂无可靠免费数据源，建议关注交易所公告'
            })

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

    def _calculate_both_strategies(self, df: pd.DataFrame, latest: pd.Series, market: str) -> Dict:
        """
        计算双策略点位（复用原来的逻辑）
        """
        try:
            current_price = latest.get('Close', 0)
            rsi = latest.get('RSI', 50)
            ma20 = latest.get('MA20', current_price)
            bb_lower = latest.get('BB_Lower', current_price * 0.9)

            if pd.isna(ma20):
                ma20 = current_price * 0.95
            if pd.isna(bb_lower):
                bb_lower = current_price * 0.9
            if pd.isna(rsi):
                rsi = 50

            # 线性策略：斐波那契回撤位
            if ma20 < current_price:
                price_range = current_price - ma20
                linear_buy = current_price - 0.5 * price_range
            else:
                linear_buy = current_price * 0.95

            linear_buy = min(linear_buy, current_price * 0.95)
            linear_stop = linear_buy * 0.92
            linear_profit = linear_buy * 1.15

            # 非线性策略：RSI超卖用布林下轨，否则20日均线
            if rsi < 30:
                nonlinear_buy = bb_lower
            else:
                nonlinear_buy = ma20

            nonlinear_stop = nonlinear_buy * 0.92
            nonlinear_profit = nonlinear_buy * 1.46

            # MACD策略：信号状态 + 操作参考（信号型策略，无固定止盈位）
            macd_info = self._calculate_macd_levels(df, latest)

            return {
                'current_price': round(current_price, 2),
                'linear': {
                    'buy': round(linear_buy, 2),
                    'stop': round(linear_stop, 2),
                    'profit': round(linear_profit, 2),
                    'distance': round((current_price - linear_buy) / current_price * 100, 2)
                },
                'nonlinear': {
                    'buy': round(nonlinear_buy, 2),
                    'stop': round(nonlinear_stop, 2),
                    'profit': round(nonlinear_profit, 2),
                    'distance': round((current_price - nonlinear_buy) / current_price * 100, 2)
                },
                'macd': macd_info
            }
        except Exception:
            # 指标数据不足等异常：返回null让前端显示占位符，绝不返回0元点位误导决策
            logger.warning("计算策略点位失败", exc_info=True)
            return {
                'current_price': None,
                'linear': {'buy': None, 'stop': None, 'profit': None, 'distance': None},
                'nonlinear': {'buy': None, 'stop': None, 'profit': None, 'distance': None},
                'macd': {'state': 'unknown', 'days_in_state': 0, 'hist': 0,
                         'add_price': None, 'stop': None, 'note': '计算失败'}
            }

    def _calculate_macd_levels(self, df: pd.DataFrame, latest: pd.Series) -> Dict:
        """
        MACD策略点位：信号状态 + 操作参考

        MACD是信号型策略（金叉买入、死叉离场），没有固定止盈位，
        因此展示：当前金叉/死叉、持续天数、加仓/关注参考价、纪律止损。
        """
        try:
            current_price = latest.get('Close', 0)
            macd = latest.get('MACD')
            signal = latest.get('MACD_Signal')
            hist = latest.get('MACD_Hist')
            ma20 = latest.get('MA20')
            bb_lower = latest.get('BB_Lower')

            if pd.isna(macd) or pd.isna(signal):
                return {'state': 'unknown', 'days_in_state': 0, 'hist': 0,
                        'add_price': None, 'stop': round(current_price * 0.92, 2),
                        'note': '指标数据不足'}

            # 当前状态：金叉（MACD>Signal）或死叉
            is_golden = macd > signal

            # 统计当前状态已持续天数
            above = df['MACD'] > df['MACD_Signal']
            days = 0
            for v in reversed(above.values.tolist()):
                if bool(v) == is_golden:
                    days += 1
                else:
                    break

            state = 'golden' if is_golden else 'death'

            # 操作参考
            add_price = round(float(ma20), 2) if pd.notna(ma20) else None       # 多头回踩MA20加仓参考
            watch_price = round(float(bb_lower), 2) if pd.notna(bb_lower) else None  # 空头关注超卖买点

            if is_golden:
                note = f'金叉第{days}天，趋势向上：持有为主，回踩MA20可考虑加仓'
            else:
                note = f'死叉第{days}天，趋势向下：观望为主，等待下一次金叉信号'

            return {
                'state': state,
                'days_in_state': days,
                'hist': round(float(hist), 4) if pd.notna(hist) else 0,
                'add_price': add_price,
                'watch_price': watch_price,
                'stop': round(current_price * 0.92, 2),  # 纪律性止损-8%
                'note': note
            }
        except Exception:
            logger.warning("计算MACD点位失败", exc_info=True)
            return {'state': 'unknown', 'days_in_state': 0, 'hist': 0,
                    'add_price': None, 'stop': None, 'note': '计算失败'}
