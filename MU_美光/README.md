# 美光科技 (MU) 分析

## 股票信息
- **股票代码**: MU
- **公司名称**: Micron Technology, Inc.
- **行业**: 半导体/存储芯片
- **主要产品**: DRAM, NAND闪存, NOR闪存

## 快速获取数据

```python
import sys
sys.path.insert(0, '..')

from utils.data_fetcher import fetch_stock_data, USStockDataFetcher

# 获取美光股票数据
df = fetch_stock_data('MU', period='2y')
print(f"获取到 {len(df)} 条数据")

# 保存到当前目录
fetcher = USStockDataFetcher(data_dir='.')
df = fetcher.get_stock_data('MU', period='2y')
fetcher.save_data(df, 'MU')
```

## 文件说明
- `MU_data.xlsx` - 美光股票历史数据（Open/High/Low/Close保留3位小数）
- `MU_analysis.ipynb` - 分析笔记本（可选）
- `MU_strategy.py` - 策略文件（可选）
