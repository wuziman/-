import api from './api';

// 单条评分记录（含至今收益）
export interface TrackingRecord {
  date: string;
  total_score: number;
  entry_price: number;
  current_price: number;
  forward_return_pct: number;
}

// 评分分桶统计
export interface TrackingBucket {
  bucket: string;
  count: number;
  avg_return: number | null;
}

// 评分追踪响应
export interface TrackingResult {
  stock_code: string;
  count: number;
  records: TrackingRecord[];
  buckets: TrackingBucket[];
  correlation: number | null;
  interpretation: string;
}

// 评分追踪API
export const trackingApi = {
  getTracking: (code: string) =>
    api.get<TrackingResult>('/analysis/tracking', { params: { stock_code: code } }),
};

export default trackingApi;
