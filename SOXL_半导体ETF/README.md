# 三倍做多半导体ETF (SOXL) 分析

## ETF信息
- **ETF代码**: SOXL
- **全称**: Direxion Daily Semiconductor Bull 3X Shares
- **类型**: 杠杆ETF（3倍做多）
- **跟踪指数**: ICE Semiconductor Index
- **风险等级**: 高风险（杠杆产品）

## 杠杆说明
- SOXL提供半导体指数的3倍每日回报
- 上涨时收益放大3倍，下跌时亏损也放大3倍
- 适合短线交易，不适合长期持有

## 快速获取数据

```python
import sys
sys.path.insert(0, '..')

from utils.data_fetcher import fetch_stock_data, USStockDataFetcher

# 获取SOXL ETF数据
df = fetch_stock_data('SOXL', period='2y')
print(f"获取到 {len(df)} 条数据")

# 保存到当前目录
fetcher = USStockDataFetcher(data_dir='.')
df = fetcher.get_stock_data('SOXL', period='2y')
fetcher.save_data(df, 'SOXL')
```

## 文件说明
- `SOXL_data.xlsx` - SOXL ETF历史数据（Open/High/Low/Close保留3位小数）
- `SOXL_analysis.ipynb` - 分析笔记本（可选）
- `SOXL_strategy.py` - 策略文件（可选）
