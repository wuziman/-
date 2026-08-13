"""
多因子选股策略模块
基于多个因子选择股票组合
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.indicators import calculate_rsi, calculate_sma, calculate_atr


class MultiFactorStrategy:
    """多因子选股策略"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital

    def calculate_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子分数

        返回:
            DataFrame: 包含各因子分数
        """
        factors = pd.DataFrame(index=df.index)

        # 1. 动量因子 (20日收益率)
        factors['Momentum_20'] = df['Close'].pct_change(20)

        # 2. 动量因子 (60日收益率)
        factors['Momentum_60'] = df['Close'].pct_change(60)

        # 3. 波动率因子 (20日波动率，取倒数)
        factors['Volatility'] = df['Close'].pct_change().rolling(20).std()
        factors['Volatility_Score'] = 1 / (factors['Volatility'] + 0.001)

        # 4. 成交量动量
        factors['Volume_Momentum'] = df['Volume'].rolling(20).mean() / df['Volume'].rolling(60).mean()

        # 5. RSI因子
        factors['RSI'] = calculate_rsi(df, 14)
        factors['RSI_Score'] = 1 - abs(factors['RSI'] - 50) / 50

        # 6. 趋势强度 (价格相对于20日均线的位置)
        sma_20 = calculate_sma(df, 20)
        factors['Trend_Strength'] = (df['Close'] - sma_20) / sma_20

        return factors

    def normalize_factors(self, factors: pd.DataFrame) -> pd.DataFrame:
        """因子标准化（Z-score）"""
        normalized = factors.copy()
        for col in factors.columns:
            mean = factors[col].mean()
            std = factors[col].std()
            if std > 0:
                normalized[col] = (factors[col] - mean) / std
            else:
                normalized[col] = 0
        return normalized

    def calculate_composite_score(
        self,
        factors: pd.DataFrame,
        weights: Dict[str, float] = None
    ) -> pd.Series:
        """
        计算综合评分

        参数:
            factors: 标准化后的因子
            weights: 因子权重
        """
        if weights is None:
            weights = {
                'Momentum_20': 0.25,
                'Momentum_60': 0.20,
                'Volatility_Score': 0.15,
                'Volume_Momentum': 0.15,
                'RSI_Score': 0.15,
                'Trend_Strength': 0.10
            }

        score = pd.Series(0.0, index=factors.index)
        for factor, weight in weights.items():
            if factor in factors.columns:
                score += factors[factor].fillna(0) * weight

        return score

    def generate_signals(
        self,
        df: pd.DataFrame,
        lookback: int = 20,
        threshold: float = 0.0
    ) -> pd.DataFrame:
        """
        生成交易信号

        参数:
            df: 原始数据
            lookback: 回看周期
            threshold: 阈值
        """
        df = df.copy()

        # 计算因子
        factors = self.calculate_factors(df)

        # 标准化
        normalized_factors = self.normalize_factors(factors)

        # 计算综合评分
        df['Score'] = self.calculate_composite_score(normalized_factors)

        # 生成信号
        df['Signal'] = 0
        df.loc[df['Score'] > threshold, 'Signal'] = 1
        df.loc[df['Score'] < -threshold, 'Signal'] = -1

        df['Trade'] = df['Signal'].diff()

        return df


class MultiStockSelector:
    """
    多股票选择器
    在多个股票中选择最优组合
    """

    def __init__(self, n_stocks: int = 10):
        self.n_stocks = n_stocks

    def rank_stocks(
        self,
        data_dict: Dict[str, pd.DataFrame],
        factor_func=None
    ) -> pd.DataFrame:
        """
        对股票进行排名

        参数:
            data_dict: {symbol: DataFrame}
            factor_func: 因子计算函数

        返回:
            DataFrame: 排名结果
        """
        rankings = []

        for symbol, df in data_dict.items():
            if len(df) < 60:  # 需要足够数据
                continue

            # 计算因子
            score = self._calculate_stock_score(df)
            rankings.append({
                'Symbol': symbol,
                'Score': score,
                'Momentum_20': df['Close'].pct_change(20).iloc[-1],
                'Momentum_60': df['Close'].pct_change(60).iloc[-1],
                'Volatility': df['Close'].pct_change().rolling(20).std().iloc[-1]
            })

        if not rankings:
            return pd.DataFrame()

        rank_df = pd.DataFrame(rankings)
        rank_df = rank_df.sort_values('Score', ascending=False)

        return rank_df

    def _calculate_stock_score(self, df: pd.DataFrame) -> float:
        """计算单只股票的综合评分"""
        # 动量 (权重40%)
        momentum_20 = df['Close'].pct_change(20).iloc[-1] if len(df) > 20 else 0
        momentum_60 = df['Close'].pct_change(60).iloc[-1] if len(df) > 60 else 0
        momentum_score = (momentum_20 * 0.6 + momentum_60 * 0.4) * 0.4

        # 波动率 (权重30%，低波动更好)
        volatility = df['Close'].pct_change().rolling(20).std().iloc[-1] if len(df) > 20 else 1
        vol_score = (1 / (volatility + 0.001)) * 0.3

        # 趋势 (权重30%)
        sma_20 = df['Close'].rolling(20).mean().iloc[-1] if len(df) > 20 else df['Close'].iloc[-1]
        trend_score = ((df['Close'].iloc[-1] / sma_20) - 1) * 0.3

        return momentum_score + vol_score + trend_score

    def select_portfolio(
        self,
        data_dict: Dict[str, pd.DataFrame],
        allocation_method: str = 'equal'
    ) -> Dict[str, float]:
        """
        选择投资组合

        参数:
            data_dict: {symbol: DataFrame}
            allocation_method: 分配方法 ('equal', 'momentum', 'risk_parity')

        返回:
            dict: {symbol: weight}
        """
        rankings = self.rank_stocks(data_dict)

        if rankings.empty:
            return {}

        # 选择前N只
        top_stocks = rankings.head(self.n_stocks)

        if allocation_method == 'equal':
            # 等权重
            weights = {row['Symbol']: 1/len(top_stocks) for _, row in top_stocks.iterrows()}

        elif allocation_method == 'momentum':
            # 按动量加权
            total_momentum = top_stocks['Momentum_20'].sum()
            if total_momentum > 0:
                weights = {row['Symbol']: row['Momentum_20']/total_momentum
                          for _, row in top_stocks.iterrows()}
            else:
                weights = {row['Symbol']: 1/len(top_stocks)
                          for _, row in top_stocks.iterrows()}

        elif allocation_method == 'risk_parity':
            # 风险平价
            inv_vol = 1 / (top_stocks['Volatility'] + 0.001)
            total_inv_vol = inv_vol.sum()
            weights = {row['Symbol']: inv_vol.iloc[i]/total_inv_vol
                      for i, (_, row) in enumerate(top_stocks.iterrows())}

        else:
            weights = {row['Symbol']: 1/len(top_stocks) for _, row in top_stocks.iterrows()}

        return weights


class CombinedStrategy:
    """
    组合策略
    结合趋势跟踪和多因子选股
    """

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.trend_strategy = None
        self.factor_strategy = MultiFactorStrategy()

    def backtest(
        self,
        data_dict: Dict[str, pd.DataFrame],
        rebalance_period: int = 20,
        trend_weight: float = 0.6,
        factor_weight: float = 0.4
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        组合回测

        参数:
            data_dict: {symbol: DataFrame}
            rebalance_period: 再平衡周期
            trend_weight: 趋势策略权重
            factor_weight: 因子策略权重
        """
        # 获取所有日期
        all_dates = set()
        for df in data_dict.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)

        if not all_dates:
            return pd.DataFrame(), {}

        # 初始化结果
        results = pd.DataFrame(index=all_dates)
        results['Capital'] = self.initial_capital
        results['Total'] = self.initial_capital
        results['Positions'] = ''

        capital = self.initial_capital
        current_positions = {}

        for i, date in enumerate(all_dates):
            # 检查是否需要再平衡
            if i % rebalance_period == 0 and i > 0:
                # 选股
                selector = MultiStockSelector(n_stocks=5)
                weights = selector.select_portfolio(data_dict, 'momentum')

                # 更新仓位
                current_positions = weights

            # 计算当日价值
            total_value = capital
            position_str = []

            for symbol, weight in current_positions.items():
                if symbol in data_dict and date in data_dict[symbol].index:
                    price = data_dict[symbol].loc[date, 'Close']
                    position_value = capital * weight
                    shares = position_value / price
                    total_value += position_value
                    position_str.append(f"{symbol}:{weight:.1%}")

            results.loc[date, 'Capital'] = capital
            results.loc[date, 'Total'] = total_value
            results.loc[date, 'Positions'] = ','.join(position_str)

        # 计算统计
        stats = self._calculate_stats(results)

        return results, stats

    def _calculate_stats(self, df: pd.DataFrame) -> Dict:
        """计算统计"""
        final_value = df['Total'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        years = len(df) / 252
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0

        # 最大回撤
        peak = df['Total'].expanding(min_periods=1).max()
        drawdown = (df['Total'] - peak) / peak
        max_drawdown = drawdown.min()

        # 夏普比率
        daily_returns = df['Total'].pct_change().dropna()
        if daily_returns.std() > 0:
            sharpe_ratio = np.sqrt(252) * (daily_returns.mean() / daily_returns.std())
        else:
            sharpe_ratio = 0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_value': final_value
        }


if __name__ == "__main__":
    from utils.data_fetcher import fetch_multiple_stocks

    # 获取多只股票数据
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    data_dict = fetch_multiple_stocks(symbols, period="1y")

    if data_dict:
        # 测试多股票选择
        selector = MultiStockSelector(n_stocks=3)
        weights = selector.select_portfolio(data_dict, 'momentum')

        print("=== 多股票选择结果 ===")
        print("\n投资组合权重:")
        for symbol, weight in weights.items():
            print(f"  {symbol}: {weight:.2%}")
