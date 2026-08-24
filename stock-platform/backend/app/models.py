"""
数据库模型
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base


class Watchlist(Base):
    """自选股列表"""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)
    market = Column(String(10), nullable=False)  # 'A' or 'US'
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisHistory(Base):
    """分析历史记录"""
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)
    tech_score = Column(Float)
    news_score = Column(Float)
    macro_score = Column(Float)
    event_score = Column(Float)
    total_score = Column(Float)
    recommendation = Column(String(20))
    price_levels = Column(JSON)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Position(Base):
    """持仓记录"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)
    market = Column(String(10), nullable=False)
    buy_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    buy_date = Column(DateTime(timezone=True), nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String(20), default="holding")  # holding, sold
    sell_price = Column(Float)          # 卖出价格（sold时填写）
    sell_date = Column(DateTime(timezone=True))  # 卖出日期
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    """平台设置（键值对，如总资金）"""
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True)
    value = Column(String(200))
