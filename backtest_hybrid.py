"""
混合策略回测系统
结合线性和非线性的优点
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class HybridBacktestEngine:
    """混合策略回测引擎"""

    def __init__(self, stock_code, start_date, end_date):
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.data = None

    def fetch_data(self):
        """获取历史数据"""
        print(f"获取 {self.stock_code} 历史数据...")
        stock = yf.Ticker(self.stock_code)
        self.data = stock.history(start=self.start_date, end=self.end_date)
        print(f"获取到 {len(self.data)} 天数据")
        return self.data

    def calculate_indicators(self):
        """计算技术指标"""
        if self.data is None:
            self.fetch_data()

        df = self.data.copy()

        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # 均线
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()

        # 布林带
        df['BB_middle'] = df['Close'].rolling(window=20).mean()
        df['BB_std'] = df['Close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + 2 * df['BB_std']
        df['BB_lower'] = df['BB_middle'] - 2 * df['BB_std']

        # 成交量比率
        df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']

        self.data = df
        return df

    def linear_signal(self):
        """线性策略信号"""
        df = self.data.copy()

        # RSI评分
        df['RSI_score'] = 0
        df.loc[df['RSI'] < 30, 'RSI_score'] = 2
        df.loc[(df['RSI'] >= 30) & (df['RSI'] < 40), 'RSI_score'] = 1
        df.loc[(df['RSI'] >= 40) & (df['RSI'] < 60), 'RSI_score'] = 0
        df.loc[(df['RSI'] >= 60) & (df['RSI'] < 70), 'RSI_score'] = -1
        df.loc[df['RSI'] >= 70, 'RSI_score'] = -2

        # MACD评分
        df['MACD_score'] = 0
        df.loc[df['MACD'] > df['Signal'], 'MACD_score'] = 1
        df.loc[df['MACD'] < df['Signal'], 'MACD_score'] = -1

        # 均线评分
        df['MA_score'] = 0
        df.loc[df['Close'] > df['MA20'], 'MA_score'] += 0.5
        df.loc[df['Close'] > df['MA50'], 'MA_score'] += 0.5
        df.loc[df['MA20'] > df['MA50'], 'MA_score'] += 0.5

        # 布林带评分
        df['BB_score'] = 0
        df.loc[df['Close'] < df['BB_lower'], 'BB_score'] = 1
        df.loc[df['Close'] > df['BB_upper'], 'BB_score'] = -1

        # 综合评分
        df['Linear_Score'] = (
            df['RSI_score'] * 0.3 +
            df['MACD_score'] * 0.3 +
            df['MA_score'] * 0.2 +
            df['BB_score'] * 0.2
        )

        # 线性信号
        df['Linear_Signal'] = 0
        df.loc[df['Linear_Score'] > 0.5, 'Linear_Signal'] = 1
        df.loc[df['Linear_Score'] < -0.5, 'Linear_Signal'] = -1

        self.data = df
        return df

    def nonlinear_signal(self):
        """非线性策略信号"""
        df = self.data.copy()

        df['NonLinear_Score'] = 0

        # 规则1：RSI超卖 + MACD金叉
        df.loc[(df['RSI'] < 30) & (df['MACD'] > df['Signal']), 'NonLinear_Score'] = 2

        # 规则2：RSI超卖 + 跌破布林带下轨
        df.loc[(df['RSI'] < 30) & (df['Close'] < df['BB_lower']), 'NonLinear_Score'] = 1.5

        # 规则3：MACD金叉 + 成交量放大
        df.loc[(df['MACD'] > df['Signal']) & (df['Volume_Ratio'] > 1.5), 'NonLinear_Score'] = 1

        # 规则4：RSI超买 + MACD死叉
        df.loc[(df['RSI'] > 70) & (df['MACD'] < df['Signal']), 'NonLinear_Score'] = -2

        # 规则5：RSI超买 + 突破布林带上轨
        df.loc[(df['RSI'] > 70) & (df['Close'] > df['BB_upper']), 'NonLinear_Score'] = -1.5

        # 规则6：MACD死叉 + 成交量放大
        df.loc[(df['MACD'] < df['Signal']) & (df['Volume_Ratio'] > 1.5), 'NonLinear_Score'] = -1

        # 非线性信号
        df['NonLinear_Signal'] = 0
        df.loc[df['NonLinear_Score'] > 0.5, 'NonLinear_Signal'] = 1
        df.loc[df['NonLinear_Score'] < -0.5, 'NonLinear_Signal'] = -1

        self.data = df
        return df

    def hybrid_signal(self):
        """混合策略信号"""
        df = self.data.copy()

        # 先计算线性和非线性信号
        self.linear_signal()
        self.nonlinear_signal()

        # 混合策略规则
        df['Hybrid_Signal'] = 0

        # 规则1：线性买入 + 非线性买入 = 强买入
        df.loc[(df['Linear_Signal'] == 1) & (df['NonLinear_Signal'] == 1), 'Hybrid_Signal'] = 2

        # 规则2：线性买入 + 非线性中性 = 买入
        df.loc[(df['Linear_Signal'] == 1) & (df['NonLinear_Signal'] == 0), 'Hybrid_Signal'] = 1

        # 规则3：线性中性 + 非线性买入 = 买入（确认信号）
        df.loc[(df['Linear_Signal'] == 0) & (df['NonLinear_Signal'] == 1), 'Hybrid_Signal'] = 1

        # 规则4：线性卖出 + 非线性卖出 = 强卖出
        df.loc[(df['Linear_Signal'] == -1) & (df['NonLinear_Signal'] == -1), 'Hybrid_Signal'] = -2

        # 规则5：线性卖出 + 非线性中性 = 卖出
        df.loc[(df['Linear_Signal'] == -1) & (df['NonLinear_Signal'] == 0), 'Hybrid_Signal'] = -1

        # 规则6：线性中性 + 非线性卖出 = 卖出（确认信号）
        df.loc[(df['Linear_Signal'] == 0) & (df['NonLinear_Signal'] == -1), 'Hybrid_Signal'] = -1

        # 转换为标准信号（1=买入，-1=卖出，0=持有）
        df['Hybrid_Signal_Standard'] = 0
        df.loc[df['Hybrid_Signal'] >= 1, 'Hybrid_Signal_Standard'] = 1
        df.loc[df['Hybrid_Signal'] <= -1, 'Hybrid_Signal_Standard'] = -1

        self.data = df
        return df

    def backtest(self, signal_column, initial_capital=10000):
        """回测策略"""
        df = self.data.copy()

        capital = initial_capital
        shares = 0
        position = 0
        trades = []
        equity_curve = []

        for i in range(1, len(df)):
            signal = df[signal_column].iloc[i]
            price = df['Close'].iloc[i]

            # 买入信号
            if signal == 1 and position == 0:
                shares = int(capital / price)
                cost = shares * price
                capital -= cost
                position = 1
                trades.append({
                    'date': df.index[i],
                    'action': 'BUY',
                    'price': price,
                    'shares': shares,
                    'cost': cost
                })

            # 卖出信号
            elif signal == -1 and position == 1:
                revenue = shares * price
                capital += revenue
                profit = revenue - trades[-1]['cost']
                trades.append({
                    'date': df.index[i],
                    'action': 'SELL',
                    'price': price,
                    'shares': shares,
                    'revenue': revenue,
                    'profit': profit
                })
                shares = 0
                position = 0

            # 记录权益曲线
            total_value = capital + shares * price
            equity_curve.append({
                'date': df.index[i],
                'equity': total_value
            })

        final_price = df['Close'].iloc[-1]
        final_value = capital + shares * final_price

        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': (final_value - initial_capital) / initial_capital * 100,
            'trades': trades,
            'equity_curve': equity_curve
        }

    def calculate_metrics(self, backtest_result):
        """计算回测指标"""
        equity_curve = pd.DataFrame(backtest_result['equity_curve'])
        equity_curve['returns'] = equity_curve['equity'].pct_change()

        total_days = len(equity_curve)
        total_return = backtest_result['total_return'] / 100
        annualized_return = (1 + total_return) ** (252 / total_days) - 1

        equity_curve['cummax'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['cummax']) / equity_curve['cummax']
        max_drawdown = equity_curve['drawdown'].min() * 100

        risk_free_rate = 0.03
        daily_returns = equity_curve['returns'].dropna()
        sharpe_ratio = (daily_returns.mean() * 252 - risk_free_rate) / (daily_returns.std() * np.sqrt(252))

        trades = backtest_result['trades']
        winning_trades = [t for t in trades if t.get('profit', 0) > 0]
        total_trades = len([t for t in trades if t['action'] == 'SELL'])
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        return {
            'annualized_return': annualized_return * 100,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_trades': total_trades
        }


def compare_all_strategies(stock_code, years=1):
    """对比所有策略"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)

    print(f"\n{'='*60}")
    print(f"策略对比: {stock_code}")
    print(f"时间段: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*60}")

    # 初始化回测引擎
    engine = HybridBacktestEngine(stock_code, start_date, end_date)
    engine.fetch_data()
    engine.calculate_indicators()

    results = {}

    # 1. 线性策略
    print("\n【1. 线性策略】")
    engine.linear_signal()
    linear_result = engine.backtest('Linear_Signal')
    linear_metrics = engine.calculate_metrics(linear_result)
    results['linear'] = linear_metrics
    print(f"年化收益: {linear_metrics['annualized_return']:.2f}%")
    print(f"最大回撤: {linear_metrics['max_drawdown']:.2f}%")
    print(f"夏普比率: {linear_metrics['sharpe_ratio']:.2f}")

    # 2. 非线性策略
    print("\n【2. 非线性策略】")
    engine.nonlinear_signal()
    nonlinear_result = engine.backtest('NonLinear_Signal')
    nonlinear_metrics = engine.calculate_metrics(nonlinear_result)
    results['nonlinear'] = nonlinear_metrics
    print(f"年化收益: {nonlinear_metrics['annualized_return']:.2f}%")
    print(f"最大回撤: {nonlinear_metrics['max_drawdown']:.2f}%")
    print(f"夏普比率: {nonlinear_metrics['sharpe_ratio']:.2f}")

    # 3. 混合策略
    print("\n【3. 混合策略】")
    engine.hybrid_signal()
    hybrid_result = engine.backtest('Hybrid_Signal_Standard')
    hybrid_metrics = engine.calculate_metrics(hybrid_result)
    results['hybrid'] = hybrid_metrics
    print(f"年化收益: {hybrid_metrics['annualized_return']:.2f}%")
    print(f"最大回撤: {hybrid_metrics['max_drawdown']:.2f}%")
    print(f"夏普比率: {hybrid_metrics['sharpe_ratio']:.2f}")

    # 对比
    print(f"\n【对比结果】")
    print(f"{'指标':<15} {'线性':<15} {'非线性':<15} {'混合':<15} {'最优'}")
    print("-" * 75)

    metrics = ['annualized_return', 'max_drawdown', 'sharpe_ratio']
    for metric in metrics:
        linear_val = results['linear'][metric]
        nonlinear_val = results['nonlinear'][metric]
        hybrid_val = results['hybrid'][metric]

        if metric == 'max_drawdown':
            # 最大回撤越小越好
            best = '混合' if hybrid_val > nonlinear_val and hybrid_val > linear_val else ('非线性' if nonlinear_val > linear_val else '线性')
        else:
            # 其他指标越大越好
            best = '混合' if hybrid_val > nonlinear_val and hybrid_val > linear_val else ('非线性' if nonlinear_val > linear_val else '线性')

        print(f"{metric:<15} {linear_val:<15.2f} {nonlinear_val:<15.2f} {hybrid_val:<15.2f} {best}")

    return results


def main():
    """主函数"""
    print("混合策略回测对比系统")
    print("=" * 60)

    # 回测股票列表
    stocks = ['MU', 'SOXL', 'COHR', 'NKE']

    all_results = []
    for stock in stocks:
        try:
            result = compare_all_strategies(stock, years=1)
            all_results.append({'stock': stock, 'results': result})
        except Exception as e:
            print(f"回测 {stock} 失败: {e}")

    # 总结
    print(f"\n{'='*60}")
    print("总结")
    print(f"{'='*60}")

    linear_wins = 0
    nonlinear_wins = 0
    hybrid_wins = 0

    for result in all_results:
        stock = result['stock']
        results = result['results']

        linear_return = results['linear']['annualized_return']
        nonlinear_return = results['nonlinear']['annualized_return']
        hybrid_return = results['hybrid']['annualized_return']

        if hybrid_return > linear_return and hybrid_return > nonlinear_return:
            hybrid_wins += 1
            print(f"{stock}: 混合策略更优 (收益: {hybrid_return:.2f}% vs 线性{linear_return:.2f}% vs 非线性{nonlinear_return:.2f}%)")
        elif nonlinear_return > linear_return:
            nonlinear_wins += 1
            print(f"{stock}: 非线性策略更优 (收益: {nonlinear_return:.2f}% vs 线性{linear_return:.2f}%)")
        else:
            linear_wins += 1
            print(f"{stock}: 线性策略更优 (收益: {linear_return:.2f}% vs 非线性{nonlinear_return:.2f}%)")

    print(f"\n最终结果:")
    print(f"线性策略胜出: {linear_wins} 次")
    print(f"非线性策略胜出: {nonlinear_wins} 次")
    print(f"混合策略胜出: {hybrid_wins} 次")

    if hybrid_wins > linear_wins and hybrid_wins > nonlinear_wins:
        print("结论: 混合策略整体更优")
    elif nonlinear_wins > linear_wins:
        print("结论: 非线性策略整体更优")
    else:
        print("结论: 线性策略整体更优")


if __name__ == "__main__":
    main()
