# 耐克 (NKE) 分析

## 股票信息
- **股票代码**: NKE
- **公司名称**: Nike, Inc.
- **行业**: 运动服饰/消费品
- **主要产品**: 运动鞋、运动服装、运动装备

## 快速获取数据

```python
import sys
sys.path.insert(0, '..')

from utils.data_fetcher import fetch_stock_data, USStockDataFetcher

# 获取耐克股票数据
df = fetch_stock_data('NKE', period='2y')
print(f"获取到 {len(df)} 条数据")

# 保存到当前目录
fetcher = USStockDataFetcher(data_dir='.')
df = fetcher.get_stock_data('NKE', period='2y')
fetcher.save_data(df, 'NKE')
```

## 文件说明
- `NKE_data.xlsx` - 耐克股票历史数据（Open/High/Low/Close保留3位小数）
- `NKE_analysis.ipynb` - 分析笔记本（可选）
- `NKE_strategy.py` - 策略文件（可选）
