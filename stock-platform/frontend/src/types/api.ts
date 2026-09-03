// 全站 API 类型唯一定义处。后端改字段名时同步这里，tsc 会在编译期报出所有失配点。

// ===== 通用 =====
export interface EquityPoint {
  date: string;
  value: number;
}

export interface KlineBar {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number;
  ma5: number | null;
  ma20: number | null;
  ma50: number | null;
  bb_upper: number | null;
  bb_mid: number | null;
  bb_lower: number | null;
}

// ===== 股票 / 自选股 =====
export interface SearchResult {
  code: string;
  name: string;
  market: string;
}

export interface WatchlistItem {
  id: number;
  stock_code: string;
  stock_name: string;
  market: string;
  created_at?: string;
}

export interface QuoteItem {
  stock_code: string;
  price: number | null;
  change_pct: number | null;
}

export interface EarningsItem {
  stock_code: string;
  stock_name: string;
  market: string;
  earnings_date: string | null;
  days_away: number | null;
}

// ===== 持仓 =====
export interface Position {
  id: number;
  stock_code: string;
  stock_name: string;
  market: string;
  buy_price: number;
  quantity: number;
  buy_date: string;
  stop_loss: number | null;
  take_profit: number | null;
  status: string;
  sell_price?: number | null;
  sell_date?: string | null;
  current_price?: number | null;
  profit_loss?: number | null;
  profit_loss_pct?: number | null;
  realized_pnl?: number | null;
  realized_pnl_pct?: number | null;
  holding_days?: number | null;
}

export interface PositionWarning {
  level: 'error' | 'warning' | 'info' | string;
  code: string;
  name: string;
  weight: number;
  message: string;
}

export interface PositionSummary {
  total_positions: number;
  total_value: number;
  total_cost: number;
  total_profit: number;
  total_profit_pct: number;
  total_capital: number;
  cash_pct: number | null;
  warnings: PositionWarning[];
}

export interface SellResponse {
  message: string;
  realized_pnl: number;
  realized_pnl_pct: number;
  holding_days: number;
}

export interface EquityCurveResponse {
  curve: EquityPoint[];
  current_drawdown_pct: number;
  max_drawdown_pct: number;
  peak_value: number;
}

// ===== 分析 =====
export interface NewsItem {
  title: string;
  source?: string;
  datetime?: string;
  sentiment?: number;
  url?: string;
}

export interface EventItem {
  name: string;
  date?: string | null;
  days_away: number | null;
  impact: string;
}

export interface AnalysisDetails {
  technical: Record<string, unknown>;
  news: {
    news_count: number;
    positive_count: number;
    negative_count: number;
    sentiment: string;
    sources?: string[];
    news: NewsItem[];
  };
  macro: {
    indicators?: Record<string, string | number | null>;
    interpretations?: string[];
  };
  event: {
    events?: EventItem[];
  };
}

export interface MarketRegimeResponse {
  vix: number;
  qqq_change: number;
  status: 'NORMAL' | 'CAUTION' | 'CIRCUIT_BREAKER' | string;
  banner: string;
  advice: string;
}

export interface EarningsRadar {
  date: string | null;
  days_away: number | null;
  tag: string;
  is_imminent: boolean;
}

export interface AnalysisResult {
  stock_code: string;
  stock_name: string;
  market: string;
  scores: {
    technical: number;
    news: number;
    macro: number;
    event: number;
    total: number;
  };
  recommendation: {
    level: string;
    action: string;
    confidence: string;
  };
  earnings_radar?: EarningsRadar;
  price_levels: {
    current_price: number | null;
    linear: PriceLevels;
    nonlinear: PriceLevels;
    macd?: {
      state: 'golden' | 'death' | 'unknown';
      days_in_state: number;
      hist: number;
      add_price: number | null;
      watch_price: number | null;
      stop: number | null;
      note: string;
    };
  };
  details: AnalysisDetails;
}

export interface PriceLevels {
  buy: number | null;
  stop: number | null;
  profit: number | null;
  distance: number | null;
}

export interface HistoryItem {
  id: number;
  stock_code: string;
  stock_name: string;
  market: string;
  total_score: number | null;
  recommendation: string | null;
  created_at: string | null;
}

// ===== 回测 =====
export interface Strategy {
  id: string;
  name: string;
  description: string;
}

export interface BacktestResult {
  stock_code: string;
  strategy: string;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  trade_count: number;
  initial_capital: number;
  final_value: number;
  equity_curve: EquityPoint[];
  period: string;
  date_range?: string;   // 自定义起止日期时由后端返回实际窗口
  trades: Array<{
    date: string;
    action: string;
    price: number;
    shares: number;
    profit_pct?: number;
    fee?: number;
  }>;
  total_fees?: number;
  commission_per_trade?: number;
  buy_hold_curve?: EquityPoint[];
  buy_hold_return?: number;   // 买入持有基准收益（后端随单次回测返回）
}

export interface CompareRow {
  name: string;
  key: string;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  trade_count: number;
  total_fees: number;
  excess_vs_buy_hold: number;
}

export interface CompareResult {
  stock_code: string;
  period: string;
  initial_capital: number;
  strategies: Record<string, BacktestResult>;
  buy_hold: {
    total_return: number;
    annual_return: number;
    max_drawdown: number;
    sharpe_ratio: number;
    equity_curve: EquityPoint[];
  };
  comparison: CompareRow[];
}

// 🎯 参数寻优
export interface OptimizeRow {
  params: Record<string, number>;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  trade_count: number;
  final_value: number;
}

export interface HeatmapData {
  x_name: string;
  y_name: string;
  x_values: number[];
  y_values: number[];
  z: Array<Array<number | null>>;
}

export interface OptimizeResult {
  stock_code: string;
  strategy: string;
  metric: string;
  period?: string;             // 回显实际回测口径
  initial_capital?: number;
  best: OptimizeRow;
  results: OptimizeRow[];
  heatmap: HeatmapData;
}

// 🔬 Walk-Forward验证
export interface WFSegment {
  step: number;
  train_range: [string, string];
  test_range: [string, string];
  best_params: Record<string, number>;
  is_sharpe: number;
  oos_return: number;
  oos_sharpe: number;
  oos_max_drawdown: number;
  oos_buy_hold_return: number;
  beats_buy_hold: boolean;
}

export interface WFResult {
  stock_code: string;
  strategy: string;
  period?: string;
  initial_capital?: number;
  train_ratio: number;
  total_segments: number;
  segments: WFSegment[];
  stitched_oos_curve: EquityPoint[];
  oos_buy_hold_curve: EquityPoint[];
  summary: {
    avg_oos_return: number;
    avg_oos_sharpe: number;
    win_segments: number;
    total_segments: number;
  };
}

// ===== 日报 / 调度 =====
export interface ReportPreview {
  report: string;
  char_count: number;
}

export interface ReportSend {
  sent: boolean;
  message?: string;
  report?: string;
  char_count?: number;
  error?: string;
}

export interface ScheduleInfo {
  enabled: boolean;
  hour: number;
  minute: number;
  last_sent_date: string | null;
}

// ===== AI选股 =====
export interface PickRecord {
  id: number;
  run_date: string;
  created_at: string | null;
  rank: number;
  stock_code: string;
  stock_name: string;
  confidence: string;
  thesis: string;
  bottlenecks: string;
  risks: string;
  catalysts: string;
  market_commentary: string;
  price_at_pick: number | null;
}

export interface StatusInfo {
  ai_configured: boolean;
  ai_model: string;
  xhs_cookie_set: boolean;
  bloggers: Array<{ name: string; url: string }>;
  cached_posts: number;
  last_run_date: string | null;
}

export interface XhsSummaryRow {
  blogger_name: string;
  summary_text: string;
  posts_count: number | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string | null;
}
