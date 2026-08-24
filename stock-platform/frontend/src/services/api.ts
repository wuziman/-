import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// 股票相关API
export const stockApi = {
  search: (query: string, market: string = 'all') =>
    api.get('/stocks/search', { params: { q: query, market } }),

  getQuote: (code: string, market: string = 'US') =>
    api.get(`/stocks/${code}/quote`, { params: { market } }),

  getHistory: (code: string, market: string = 'US', period: string = '3mo') =>
    api.get(`/stocks/${code}/history`, { params: { market, period } }),

  getWatchlist: () =>
    api.get('/stocks/watchlist'),

  // 自选股财报日历（美股yfinance；A股拿不到则日期为空）
  getEarningsCalendar: () =>
    api.get('/stocks/earnings-calendar'),

  addToWatchlist: (data: { stock_code: string; stock_name: string; market: string }) =>
    api.post('/stocks/watchlist', data),

  removeFromWatchlist: (id: number) =>
    api.delete(`/stocks/watchlist/${id}`),
};

// 分析相关API
export const analysisApi = {
  analyze: (data: { stock_code: string; stock_name: string; mode?: string }) =>
    api.post('/analysis', data),

  saveAnalysis: (data: any) =>
    api.post('/analysis/save', data),

  getHistory: (stockCode?: string, limit: number = 20) =>
    api.get('/analysis/history', { params: { stock_code: stockCode, limit } }),

  getDetail: (id: number) =>
    api.get(`/analysis/history/${id}`),
};

// 回测相关API
export const backtestApi = {
  getStrategies: () =>
    api.get('/backtest/strategies'),

  runBacktest: (data: {
    stock_code: string;
    strategy: string;
    period?: string;
    start_date?: string;
    end_date?: string;
    initial_capital?: number;
    commission_per_trade?: number;
  }) => api.post('/backtest', data),

  // 一键对比4策略 + 买入持有基准
  compare: (data: {
    stock_code: string;
    period?: string;
    initial_capital?: number;
    commission_per_trade?: number;
  }) => api.post('/backtest/compare', data),

  // 🎯 参数网格寻优
  optimize: (data: {
    stock_code: string;
    strategy: string;
    period?: string;
    initial_capital?: number;
    commission_per_trade?: number;
    metric?: string;
  }) => api.post('/backtest/optimize', data),

  // 🔬 Walk-Forward滚动验证
  walkForward: (data: {
    stock_code: string;
    strategy: string;
    period?: string;
    initial_capital?: number;
    commission_per_trade?: number;
    train_ratio?: number;
    segments?: number;
  }) => api.post('/backtest/walkforward', data),
};

// 持仓相关API
export const portfolioApi = {
  getPositions: () =>
    api.get('/portfolio'),

  getHistory: () =>
    api.get('/portfolio/history'),

  sellPosition: (id: number, data: { sell_price: number; sell_date: string }) =>
    api.post(`/portfolio/${id}/sell`, data),

  addPosition: (data: {
    stock_code: string;
    stock_name: string;
    market: string;
    buy_price: number;
    quantity: number;
    buy_date: string;
    stop_loss?: number;
    take_profit?: number;
  }) => api.post('/portfolio', data),

  updatePosition: (id: number, data: {
    buy_price?: number;
    quantity?: number;
    buy_date?: string;
    stop_loss?: number | null;
    take_profit?: number | null;
  }) => api.put(`/portfolio/${id}`, data),

  deletePosition: (id: number) =>
    api.delete(`/portfolio/${id}`),

  getSummary: () =>
    api.get('/portfolio/summary'),

  // 组合净值曲线 + 回撤统计（每日快照由后台监控任务写入）
  getEquityCurve: () =>
    api.get('/portfolio/equity-curve'),

  getTotalCapital: () =>
    api.get('/portfolio/settings/total_capital'),

  setTotalCapital: (total_capital: number) =>
    api.put(`/portfolio/settings/total_capital?total_capital=${total_capital}`),
};

// 日报API
export const reportApi = {
  preview: () => api.get('/report/preview'),
  send: (dryRun: boolean) => api.post('/report/send', { dry_run: dryRun }),
};

// AI选股API
export const aiPickApi = {
  getStatus: () => api.get('/ai-pick/status'),

  // 运行一次完整AI选股（LLM分析耗时较长）
  run: () => api.post('/ai-pick/run', null, { timeout: 300000 }),

  getHistory: (limit: number = 30) =>
    api.get('/ai-pick/history', { params: { limit } }),

  getXhsConfig: () => api.get('/ai-pick/xhs-config'),

  saveXhsConfig: (data: { cookie?: string | null; bloggers?: Array<{ name: string; url: string }> | null }) =>
    api.put('/ai-pick/xhs-config', data),

  refreshXhs: () => api.post('/ai-pick/xhs-refresh', null, { timeout: 120000 }),

  listXhsPosts: (limit: number = 20) =>
    api.post('/ai-pick/xhs-posts', { limit }),

  getXhsSummaries: () => api.get('/ai-pick/xhs-summaries'),

  generateXhsSummaries: () => api.post('/ai-pick/xhs-summaries', null, { timeout: 300000 }),
};

export default api;
