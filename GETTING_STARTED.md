# 美股量化投资系统 - 快速开始指南

## 🎯 如何获取真实数据

### 方法1: 直接运行回测（推荐）

```bash
cd "C:\Users\wuzim\Desktop\股票投资"

# 回测苹果股票
python real_data_backtest.py
```

### 方法2: 单行命令获取数据

```python
from utils.data_fetcher import fetch_stock_data

# 获取苹果股票2年数据
df = fetch_stock_data('AAPL', period='2y')
print(df.head())
```

### 方法3: 批量获取多只股票

```python
from utils.data_fetcher import fetch_multiple_stocks

# 批量获取5只科技股
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
data = fetch_multiple_stocks(symbols, period='1y')

for symbol, df in data.items():
    print(f"{symbol}: {len(df)} 条数据")
```

### 方法4: 保存数据到本地

```python
from utils.data_fetcher import USStockDataFetcher

fetcher = USStockDataFetcher()
df = fetcher.get_stock_data('AAPL', period='2y')
fetcher.save_data(df, 'AAPL')  # 保存到 data/AAPL_data.csv
```

---

## 📊 完整回测示例

```python
from utils.data_fetcher import fetch_stock_data
from strategies.trend_following import DualMovingAverage, backtest_strategy

# 1. 获取数据
df = fetch_stock_data('AAPL', period='1y')
df = df.dropna()

# 2. 创建策略
strategy = DualMovingAverage(short_period=20, long_period=50)

# 3. 回测
results, stats = backtest_strategy(df, strategy)

# 4. 查看结果
print(f"年化收益率: {stats['annual_return']:.2%}")
print(f"最大回撤: {stats['max_drawdown']:.2%}")
print(f"夏普比率: {stats['sharpe_ratio']:.2f}")
```

---

## 🎯 常用股票代码

| 公司 | 代码 |
|------|------|
| 苹果 | AAPL |
| 微软 | MSFT |
| 谷歌 | GOOGL |
| 亚马逊 | AMZN |
| 英伟达 | NVDA |
| 特斯拉 | TSLA |
| Meta | META |

---

## ⚠️ 注意事项

1. **网络连接**: 需要网络连接获取Yahoo Finance数据
2. **数据清洗**: 建议使用 `df.dropna()` 清理缺失值
3. **数据量**: 至少需要60天以上数据用于计算指标
4. **时区**: 数据使用美国东部时间

---

## 🚀 运行完整示例

```bash
# 快速入门（使用模拟数据）
python quick_start.py

# 真实数据回测
python real_data_backtest.py

# 主程序（完整功能）
python main.py
```

---

## 📁 数据存储位置

获取的数据会保存在 `data/` 目录下：
- `data/AAPL_data.csv`
- `data/MSFT_data.csv`
- 等等...

你可以直接查看或导入这些CSV文件。
