"""
美股数据获取模块
支持从Yahoo Finance获取历史数据
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import os


class USStockDataFetcher:
    """美股数据获取器"""

    def __init__(self, data_dir: str = None):
        # 默认保存到项目根目录的data文件夹
        if data_dir is None:
            # 获取项目根目录（utils的上级目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            data_dir = os.path.join(project_root, "data")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def get_stock_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = "2y"
    ) -> pd.DataFrame:
        """
        获取单只股票的历史数据

        参数:
            symbol: 股票代码，如'AAPL', 'GOOGL'
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            period: 时间段 '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max'

        返回:
            DataFrame: 包含OHLCV数据
        """
        try:
            stock = yf.Ticker(symbol)

            if start_date and end_date:
                df = stock.history(start=start_date, end=end_date)
            else:
                df = stock.history(period=period)

            if df.empty:
                print(f"警告: 未获取到 {symbol} 的数据")
                return pd.DataFrame()

            # 过滤盘前空占位行
            df = df.dropna(subset=['Close'])
            if df.empty:
                print(f"警告: {symbol} 数据有效收盘价为空")
                return pd.DataFrame()

            # 添加股票代码列
            df['Symbol'] = symbol
            df.index.name = 'Date'

            return df

        except Exception as e:
            print(f"获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()

    def get_multiple_stocks(
        self,
        symbols: List[str],
        start_date: str = None,
        end_date: str = None,
        period: str = "2y"
    ) -> dict:
        """
        批量获取多只股票数据

        参数:
            symbols: 股票代码列表
            其他参数同get_stock_data

        返回:
            dict: {symbol: DataFrame}
        """
        data_dict = {}
        for symbol in symbols:
            df = self.get_stock_data(symbol, start_date, end_date, period)
            if not df.empty:
                data_dict[symbol] = df
                print(f"[OK] {symbol}: {len(df)} 条数据")
            else:
                print(f"[FAIL] {symbol}: 无数据")
        return data_dict

    def get_sp500_components(self) -> List[str]:
        """获取标普500成分股列表（简化版）"""
        # 常见的大盘股列表
        sp500_top50 = [
            'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'BRK-B',
            'UNH', 'JNJ', 'JPM', 'V', 'PG', 'XOM', 'HD', 'CVX', 'MA', 'ABBV',
            'MRK', 'LLY', 'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'MCD', 'WMT',
            'CSCO', 'ACN', 'ABT', 'DHR', 'NEE', 'LIN', 'PM', 'TXN', 'UNP',
            'RTX', 'LOW', 'HON', 'UPS', 'AMGN', 'IBM', 'QCOM', 'SPGI', 'BA',
            'CAT', 'GE', 'BLK', 'AXP', 'MDLZ'
        ]
        return sp500_top50

    def get_etf_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = "2y"
    ) -> pd.DataFrame:
        """获取ETF数据（接口与股票相同）"""
        return self.get_stock_data(symbol, start_date, end_date, period)

    def save_data(self, df: pd.DataFrame, symbol: str) -> str:
        """保存数据到Excel (.xlsx)"""
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        filename = f"{self.data_dir}/{symbol}_data.xlsx"

        # 对Open, High, Low, Close四列保留3位小数
        df_to_save = df.copy()
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].round(3)

        # 移除时区信息（Excel不支持带时区的datetime）
        if df_to_save.index.tz is not None:
            df_to_save.index = df_to_save.index.tz_localize(None)

        # 过滤掉价格为NaN的行（当天数据不完整）
        df_to_save = df_to_save.dropna(subset=['Close'])

        # 将索引转换为Date列
        df_to_save = df_to_save.reset_index()

        try:
            df_to_save.to_excel(filename, index=False, engine='openpyxl')
            print(f"数据已保存: {filename}")
            return filename
        except Exception as e:
            print(f"保存失败: {e}")
            # 尝试保存到当前目录
            filename = f"{symbol}_data.xlsx"
            df_to_save.to_excel(filename, index=False, engine='openpyxl')
            print(f"数据已保存到: {filename}")
            return filename

    def load_data(self, symbol: str) -> pd.DataFrame:
        """从Excel加载数据"""
        filename = f"{self.data_dir}/{symbol}_data.xlsx"
        if os.path.exists(filename):
            df = pd.read_excel(filename, engine='openpyxl')
            # 将Date列转换为日期并设置为索引
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            return df
        else:
            print(f"文件不存在: {filename}")
            return pd.DataFrame()


# 便捷函数
def fetch_stock_data(symbol: str, period: str = "2y") -> pd.DataFrame:
    """快速获取股票数据"""
    fetcher = USStockDataFetcher()
    return fetcher.get_stock_data(symbol, period=period)


def fetch_multiple_stocks(symbols: List[str], period: str = "2y") -> dict:
    """快速获取多只股票数据"""
    fetcher = USStockDataFetcher()
    return fetcher.get_multiple_stocks(symbols, period=period)


if __name__ == "__main__":
    # 测试数据获取
    fetcher = USStockDataFetcher()

    # 获取苹果股票数据
    aapl = fetcher.get_stock_data("AAPL", period="1y")
    print(f"\nAAPL 数据预览:")
    print(aapl.tail())
    print(f"\n数据形状: {aapl.shape}")
