# 美股量化投资系统

一个完整的美股量化投资框架，包含数据获取、策略开发、回测和风险管理。

## 📁 项目结构

```
stock-investment/
├── data/                  # 数据存储目录
├── strategies/           # 策略模块
│   ├── trend_following.py    # 趋势跟踪策略
│   └── multi_factor.py       # 多因子选股策略
├── risk/                 # 风控模块
│   └── position_sizing.py    # 仓位管理
├── utils/                # 工具函数
│   ├── data_fetcher.py       # 数据获取
│   ├── indicators.py         # 技术指标
│   └── visualization.py      # 可视化
├── main.py               # 主程序
└── requirements.txt      # 依赖包
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行回测

```python
from main import QuantSystem

# 创建系统实例
system = QuantSystem()

# 单股票回测
system.run_single_stock_backtest("AAPL", "dual_ma", period="2y")

# 多股票回测
system.run_multi_stock_backtest(
    ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
    "dual_ma",
    period="1y"
)

# 参数优化
best_params, best_stats, _ = system.optimize_strategy(
    "AAPL", "dual_ma", period="2y"
)
```

### 3. 直接运行

```bash
python main.py
```

## 📊 可用策略

### 趋势跟踪策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `dual_ma` | 双均线交叉 | 趋势明显的市场 |
| `macd` | MACD金叉死叉 | 中期趋势 |
| `rsi` | RSI超买超卖 | 震荡市场 |
| `supertrend` | 超级趋势 | 强趋势市场 |
| `turtle` | 海龟交易 | 长期趋势 |
| `momentum` | 动量策略 | 追涨杀跌 |

### 多因子选股

- 动量因子（20日、60日收益率）
- 波动率因子（低波动更好）
- 成交量动量
- RSI因子
- 趋势强度

## 📈 技术指标

系统内置以下技术指标：

- **移动平均**: SMA, EMA
- **震荡指标**: RSI, MACD, Stochastic
- **趋势指标**: ADX, ATR, SuperTrend
- **波动指标**: Bollinger Bands
- **成交量**: OBV, VWAP

## 🛡️ 风险管理

### 仓位管理
- 基于风险的仓位计算
- 凯利公式仓位优化
- 相关性约束

### 止损策略
- 初始止损（固定百分比）
- 移动止损（跟踪最高价）
- ATR止损（基于波动率）
- 时间止损（持仓时间限制）

### 风险控制
- 单笔交易风险限制（默认2%）
- 单日亏损限制（默认3%）
- 最大回撤限制（默认20%）

## 🎯 使用示例

### 示例1: 测试苹果股票

```python
from utils.data_fetcher import fetch_stock_data
from strategies import DualMovingAverage, backtest_strategy

# 获取数据
df = fetch_stock_data("AAPL", period="2y")

# 创建策略
strategy = DualMovingAverage(short_period=20, long_period=50)

# 回测
results, stats = backtest_strategy(df, strategy)

# 打印结果
print(f"总收益率: {stats['total_return']:.2%}")
print(f"年化收益率: {stats['annual_return']:.2%}")
print(f"最大回撤: {stats['max_drawdown']:.2%}")
```

### 示例2: 策略对比

```python
from main import QuantSystem

system = QuantSystem()

# 对比多个策略
for strategy_name in ["dual_ma", "macd", "rsi", "supertrend"]:
    system.run_single_stock_backtest("AAPL", strategy_name, period="2y")

# 查看对比结果
system.generate_report()
```

### 示例3: 参数优化

```python
from main import QuantSystem

system = QuantSystem()

# 定义参数网格
param_grid = {
    'short_period': [10, 20, 30, 40],
    'long_period': [50, 100, 150, 200]
}

# 优化
best_params, best_stats, all_results = system.optimize_strategy(
    "AAPL",
    "dual_ma",
    param_grid=param_grid,
    period="2y"
)

print(f"最优参数: {best_params}")
```

## 📊 可视化

```python
from utils.visualization import (
    plot_backtest_results,
    plot_strategy_comparison,
    plot_monthly_returns
)

# 绘制单策略结果
plot_backtest_results(results, title="AAPL 双均线策略")

# 绘制策略对比
plot_strategy_comparison(all_results, title="策略对比")

# 绘制月度收益
plot_monthly_returns(results, title="月度收益分布")
```

## 📋 输出示例

```
============================================================
📊 AAPL - dual_ma 回测结果
────────────────────────────────────────────
💰 总收益率:        45.23%
📈 年化收益率:      22.41%
📉 最大回撤:       -15.67%
⚡ 夏普比率:        1.85
🎯 交易次数:          12
✅ 胜率:          58.33%
💵 最终资金:   145,230.00
────────────────────────────────────────────
```

## ⚠️ 注意事项

1. **数据质量**: 依赖Yahoo Finance数据，可能有延迟
2. **滑点和手续费**: 回测中默认0.1%，实盘可能更高
3. **过拟合**: 参数优化可能导致过拟合，建议样本外测试
4. **市场风险**: 历史表现不代表未来收益
5. **资金安全**: 请勿将全部资金投入单一策略

## 🔧 自定义扩展

### 添加新策略

```python
from strategies.trend_following import TrendFollowingStrategy

class MyStrategy(TrendFollowingStrategy):
    def generate_signals(self, df):
        # 实现你的策略逻辑
        df['Signal'] = 0
        # ... 生成信号
        df['Trade'] = df['Signal'].diff()
        return df
```

### 添加新指标

```python
from utils.indicators import calculate_sma

def my_indicator(df, period=20):
    # 实现你的指标
    return my_result
```

## 📚 参考资料

- [Backtrader文档](https://www.backtrader.com/)
- [TA-Lib文档](https://ta-lib.github.io/ta-lib-python/)
- [QuantConnect](https://www.quantconnect.com/)
- [Quantopian](https://www.quantopian.com/)

## 📝 许可证

MIT License
