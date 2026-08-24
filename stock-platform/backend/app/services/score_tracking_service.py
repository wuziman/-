"""
评分追踪服务（纯逻辑，便于测试）：
把历史评分记录与后续行情结合，验证评分体系对收益的预测力
"""

from bisect import bisect_right
from math import sqrt
from typing import Dict, List, Optional


def _record_get(record, key):
    """兼容 dict 与 ORM 对象两种记录形态"""
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key, None)


def _norm_date_str(value) -> Optional[str]:
    """把 datetime/date/Timestamp/'YYYY-MM-DD ...' 统一为 'YYYY-MM-DD' 字符串"""
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    return s[:10] if s else None


def compute_forward_returns(
    records: List,
    closes: Dict[str, float],
    current_price: Optional[float],
) -> List[Dict]:
    """
    为每条评分记录匹配入场价并计算"至今"收益率

    - entry_price：收盘价中 <= 记录日期 的最近一日收盘
      （周末/节假日等非交易日期自动取前一交易日）
    - 记录早于所有交易日、closes为空、无当前价 → 该条跳过

    返回：[{"date","total_score","entry_price","current_price","forward_return_pct"}...]
    """
    matched: List[Dict] = []
    if not closes or not current_price:
        return matched

    dates = sorted(closes.keys())  # ISO日期字符串按字典序即时间序
    for rec in records:
        raw_date = _record_get(rec, "date")
        if raw_date is None:
            raw_date = _record_get(rec, "created_at")  # ScoreHistory ORM行的字段名
        d = _norm_date_str(raw_date)
        if not d:
            continue
        idx = bisect_right(dates, d)
        if idx == 0:
            continue  # 早于所有交易日
        entry_date = dates[idx - 1]
        entry_price = closes[entry_date]
        forward_return_pct = round((current_price / entry_price - 1) * 100, 2)
        matched.append({
            "date": d,
            "total_score": _record_get(rec, "total_score"),
            "entry_price": entry_price,
            "current_price": current_price,
            "forward_return_pct": forward_return_pct,
        })
    return matched


# 分桶定义：左闭右开，最后一桶含上界
_BUCKETS = [
    ("<5分", lambda s: s < 5),
    ("5~6.5分", lambda s: 5 <= s < 6.5),
    ("6.5~8分", lambda s: 6.5 <= s < 8),
    ("≥8分", lambda s: s >= 8),
]


def bucket_stats(records: List) -> List[Dict]:
    """
    按评分区间统计次数与平均后续收益

    返回：[{"bucket","count","avg_return"},...]（avg保留2位，无样本时为None）
    """
    counts = [0] * len(_BUCKETS)
    ret_sums = [0.0] * len(_BUCKETS)
    ret_counts = [0] * len(_BUCKETS)

    for rec in records:
        score = _record_get(rec, "total_score")
        ret = _record_get(rec, "forward_return_pct")
        if score is None:
            continue
        for i, (_, cond) in enumerate(_BUCKETS):
            if cond(score):
                counts[i] += 1
                if ret is not None:
                    ret_sums[i] += ret
                    ret_counts[i] += 1
                break

    return [
        {
            "bucket": label,
            "count": counts[i],
            "avg_return": round(ret_sums[i] / ret_counts[i], 2) if ret_counts[i] else None,
        }
        for i, (label, _) in enumerate(_BUCKETS)
    ]


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """
    手写皮尔逊相关系数；n<5 或任一序列方差为0时返回None
    """
    n = len(xs)
    if n != len(ys) or n < 5:
        return None

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return round(cov / sqrt(var_x * var_y), 4)


def _interpret_correlation(corr: Optional[float]) -> str:
    """相关性解读文案"""
    if corr is None:
        return "相关性弱，样本可能不足"
    if corr > 0.3:
        return "评分与后续收益正相关，体系有效"
    if corr < -0.3:
        return "负相关，建议调整权重"
    return "相关性弱，样本可能不足"


def build_tracking(stock_code: str, db_rows: List, history_df=None) -> Dict:
    """
    主入口：评分记录 × 后续行情 → 追踪报告

    - db_rows：ScoreHistory查询结果（升序），dict或ORM对象均可
    - history_df：历史行情DataFrame（DatetimeIndex + Close列），可为None
    - count：累计评分次数（含无法匹配行情的记录）
    """
    rows = list(db_rows)

    # 历史收盘价 → {date_str: close}，最新价取最后一个close
    closes: Dict[str, float] = {}
    current_price: Optional[float] = None
    if history_df is not None and not history_df.empty and "Close" in history_df.columns:
        for idx, row in history_df.iterrows():
            try:
                close = float(row["Close"])
            except (TypeError, ValueError):
                continue
            if close != close:  # NaN
                continue
            closes[_norm_date_str(idx)] = close
        if closes:
            current_price = closes[sorted(closes.keys())[-1]]

    records = compute_forward_returns(rows, closes, current_price)
    correlation = pearson(
        [r["total_score"] for r in records],
        [r["forward_return_pct"] for r in records],
    )

    return {
        "stock_code": stock_code,
        "count": len(rows),
        "records": records,
        "buckets": bucket_stats(records),
        "correlation": correlation,
        "interpretation": _interpret_correlation(correlation),
    }
