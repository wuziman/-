# -*- coding: utf-8 -*-
"""
自动化测试：评分追踪纯逻辑（前向收益/分桶/相关性/全链路）
运行：cd backend && python -m pytest tests/test_score_tracking.py -v
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base
from app.services.score_tracking_service import (
    bucket_stats,
    build_tracking,
    compute_forward_returns,
    pearson,
)


# 测试用收盘价：2025-01-06(周一) ~ 2025-01-10(周五)
CLOSES = {
    "2025-01-03": 90.0,
    "2025-01-06": 100.0,
    "2025-01-07": 110.0,
    "2025-01-08": 120.0,
    "2025-01-09": 130.0,
    "2025-01-10": 140.0,
}
CURRENT = 105.0


def _rec(date, score):
    return {"date": date, "total_score": score}


class TestComputeForwardReturns:
    def test_weekend_takes_previous_trading_day(self):
        # 2025-01-11是周六 → 取最近前一交易日01-10收盘140
        out = compute_forward_returns([_rec("2025-01-11", 7.0)], CLOSES, CURRENT)
        assert len(out) == 1
        assert out[0]["entry_price"] == 140.0
        assert out[0]["forward_return_pct"] == round((105 / 140 - 1) * 100, 2)  # -25.0
        assert out[0]["date"] == "2025-01-11"
        assert out[0]["current_price"] == CURRENT

    def test_exact_trading_day_uses_same_day_close(self):
        out = compute_forward_returns([_rec("2025-01-07", 6.0)], CLOSES, CURRENT)
        assert out[0]["entry_price"] == 110.0
        assert out[0]["forward_return_pct"] == round((105 / 110 - 1) * 100, 2)  # -4.55

    def test_date_before_all_closes_skipped(self):
        # 早于所有交易日（01-02）→ 跳过
        out = compute_forward_returns(
            [_rec("2025-01-02", 8.0), _rec("2025-01-08", 5.0)], CLOSES, CURRENT
        )
        assert len(out) == 1
        assert out[0]["date"] == "2025-01-08"

    def test_datetime_object_accepted(self):
        out = compute_forward_returns(
            [_rec(datetime(2025, 1, 9), 7.5)], CLOSES, CURRENT
        )
        assert len(out) == 1
        assert out[0]["entry_price"] == 130.0

    def test_orm_style_row_uses_created_at(self):
        # ScoreHistory ORM行没有date字段，日期在created_at
        class FakeRow:
            created_at = datetime(2025, 1, 9)
            total_score = 6.8

        out = compute_forward_returns([FakeRow()], CLOSES, CURRENT)
        assert len(out) == 1
        assert out[0]["entry_price"] == 130.0
        assert out[0]["total_score"] == 6.8

    def test_empty_closes_or_no_price(self):
        assert compute_forward_returns([_rec("2025-01-08", 6.0)], {}, CURRENT) == []
        assert compute_forward_returns([_rec("2025-01-08", 6.0)], CLOSES, None) == []

    def test_record_fields(self):
        out = compute_forward_returns([_rec("2025-01-06", 8.2)], CLOSES, CURRENT)
        r = out[0]
        assert set(r.keys()) == {
            "date", "total_score", "entry_price", "current_price", "forward_return_pct"
        }
        assert r["total_score"] == 8.2


class TestBucketStats:
    def test_boundaries(self):
        records = [
            {"total_score": 4.99, "forward_return_pct": 10.0},   # <5
            {"total_score": 5.0, "forward_return_pct": -5.0},    # [5, 6.5)
            {"total_score": 6.5, "forward_return_pct": 0.0},     # [6.5, 8)
            {"total_score": 7.99, "forward_return_pct": 3.0},    # [6.5, 8)
            {"total_score": 8.0, "forward_return_pct": 9.0},     # >=8
            {"total_score": 9.0, "forward_return_pct": 11.0},    # >=8
        ]
        buckets = bucket_stats(records)
        assert [b["bucket"] for b in buckets] == ["<5分", "5~6.5分", "6.5~8分", "≥8分"]
        assert [b["count"] for b in buckets] == [1, 1, 2, 2]
        assert [b["avg_return"] for b in buckets] == [10.0, -5.0, 1.5, 10.0]

    def test_avg_rounding(self):
        records = [
            {"total_score": 9.0, "forward_return_pct": 1.111},
            {"total_score": 9.1, "forward_return_pct": 2.222},
        ]
        buckets = bucket_stats(records)
        assert buckets[3]["avg_return"] == round((1.111 + 2.222) / 2, 2)

    def test_empty(self):
        buckets = bucket_stats([])
        assert len(buckets) == 4
        assert all(b["count"] == 0 and b["avg_return"] is None for b in buckets)


class TestPearson:
    def test_perfect_positive(self):
        r = pearson([1, 2, 3, 4, 5], [10, 20, 30, 40, 50])
        assert r is not None and abs(r - 1) < 1e-6

    def test_perfect_negative(self):
        r = pearson([1, 2, 3, 4, 5], [50, 40, 30, 20, 10])
        assert r is not None and abs(r + 1) < 1e-6

    def test_constant_series_none(self):
        assert pearson([1, 2, 3, 4, 5], [7, 7, 7, 7, 7]) is None
        assert pearson([3, 3, 3, 3, 3], [1, 2, 3, 4, 5]) is None

    def test_small_sample_none(self):
        assert pearson([1, 2, 3, 4], [2, 4, 6, 8]) is None

    def test_length_mismatch_none(self):
        assert pearson([1, 2, 3, 4, 5], [1, 2, 3]) is None


class TestBuildTracking:
    def _make_df(self):
        dates = ["2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10"]
        return pd.DataFrame(
            {"Close": [CLOSES[d] for d in dates]},
            index=pd.to_datetime(dates),
        )

    def test_full_pipeline_structure(self):
        rows = [
            {"stock_code": "MU", "date": datetime(2025, 1, 7), "total_score": 8.5},
            {"stock_code": "MU", "date": datetime(2025, 1, 11), "total_score": 4.2},
            {"stock_code": "MU", "date": datetime(2025, 1, 2), "total_score": 6.0},  # 跳过
        ]
        result = build_tracking("MU", rows, self._make_df())

        # 结构完整
        assert set(result.keys()) == {
            "stock_code", "count", "records", "buckets", "correlation", "interpretation"
        }
        # count=累计评分次数（含被跳过的）
        assert result["count"] == 3
        # 仅2条匹配到入场价，且保持升序
        assert [r["date"] for r in result["records"]] == ["2025-01-07", "2025-01-11"]
        # 最新价=最后一个close
        assert all(r["current_price"] == 140.0 for r in result["records"])
        # 分桶4桶齐全，次数合计=匹配数
        assert len(result["buckets"]) == 4
        assert sum(b["count"] for b in result["buckets"]) == 2

    def test_correlation_and_interpretation(self):
        dates = [f"2025-01-{d:02d}" for d in range(1, 16)]  # 15条记录
        rows = [
            {"date": d, "total_score": (i % 9) + 1}
            for i, d in enumerate(dates)
        ]
        df = pd.DataFrame(
            {"Close": [float(i + 10) for i in range(len(dates))]},
            index=pd.to_datetime(dates),
        )
        result = build_tracking("TEST", rows, df)
        assert isinstance(result["correlation"], float)
        assert result["interpretation"] in (
            "评分与后续收益正相关，体系有效",
            "负相关，建议调整权重",
            "相关性弱，样本可能不足",
        )

    def test_no_market_data_graceful(self):
        rows = [{"date": "2025-01-08", "total_score": 7.0}]
        result = build_tracking("MU", rows, None)
        assert result["count"] == 1
        assert result["records"] == []
        assert result["correlation"] is None
        assert result["interpretation"] == "相关性弱，样本可能不足"


class TestModelRegistration:
    def test_score_history_registered_on_base(self):
        # router import本模块后，create_all之前必须已注册到Base.metadata
        from app.models_tracking import ScoreHistory  # noqa: F401
        assert "score_history" in Base.metadata.tables
        cols = ScoreHistory.__table__.columns.keys()
        for c in ("stock_code", "total_score", "price_at_score", "created_at"):
            assert c in cols
