"""
平台扩展表模型（与models.py分离，避免并行开发冲突）
"""

from sqlalchemy import Column, Float, Integer, String, Text, DateTime
from .database import Base


class KlineCache(Base):
    """K线数据缓存表（降低yfinance/新浪接口重复拉取耗时）"""
    __tablename__ = "kline_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(100), unique=True, index=True, nullable=False)  # 格式: {market}:{code}:{period}
    data_json = Column(Text, nullable=False)      # DataFrame序列化后的JSON（日期为字符串）
    fetched_at = Column(DateTime, nullable=False)  # 拉取时间（本地时间），用于TTL判断


class PriceAlertLog(Base):
    """止损止盈触发记录表（同一天同一持仓同一类型只推一次微信）

    position_id=0 为保留值，表示组合级告警（如回撤破线），此时stock_code存'drawdown'
    """
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, index=True, nullable=False, default=0)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(50))
    alert_type = Column(String(20), nullable=False)   # stop_loss / take_profit / drawdown
    price = Column(Float)                              # 触发时现价（drawdown为当前组合市值）
    triggered_date = Column(String(10), index=True, nullable=False)  # 'YYYY-MM-DD'，按天去重
    created_at = Column(DateTime)


class PortfolioSnapshot(Base):
    """组合每日净值快照（净值曲线与回撤监控数据源）"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snap_date = Column(String(10), unique=True, index=True, nullable=False)  # 'YYYY-MM-DD'，同日更新覆盖
    total_value = Column(Float, nullable=False)     # 当日组合总市值（最新一次计算值）
    created_at = Column(DateTime)


class AIPick(Base):
    """AI选股结果（Serenity供应链卡点思维，仅美股）"""
    __tablename__ = "ai_picks"

    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(String(10), index=True, nullable=False)   # 运行日期 'YYYY-MM-DD'
    rank = Column(Integer, nullable=False)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(50))
    confidence = Column(String(10))                 # high / medium / low
    thesis = Column(Text)                           # 核心论点
    bottlenecks = Column(Text)                      # 供应链卡点分析
    risks = Column(Text)                            # 压力测试/最大反方观点
    catalysts = Column(Text)                        # 催化剂
    market_commentary = Column(Text)                # 本次运行的行业综述
    price_at_pick = Column(Float)                   # 选股时价格（后续追踪用）
    evidence_json = Column(Text)                    # 引用的数据来源（新闻/小红书帖子）
    created_at = Column(DateTime)


class XhsPost(Base):
    """小红书博主帖子缓存（按note_id去重，供AI选股作为输入源）"""
    __tablename__ = "xhs_posts"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(String(64), unique=True, index=True, nullable=False)
    blogger_name = Column(String(100))
    title = Column(Text)
    content = Column(Text)
    url = Column(String(200))
    posted_time = Column(String(30))
    fetched_at = Column(DateTime)


class XhsSummary(Base):
    """博主帖子AI总结（每博主一行，新总结覆盖旧值，供用户快速浏览）"""
    __tablename__ = "xhs_summaries"

    id = Column(Integer, primary_key=True, index=True)
    blogger_name = Column(String(100), unique=True, index=True, nullable=False)
    summary_text = Column(Text, nullable=False)    # LLM生成的中文总结正文
    posts_count = Column(Integer)                  # 总结覆盖的帖子条数
    period_start = Column(String(10))              # 覆盖的最早帖子日期 'YYYY-MM-DD'
    period_end = Column(String(10))                # 覆盖的最新帖子日期
    created_at = Column(DateTime)
