import api from './api';

// K线形态
export interface PatternSignal {
  date: string;
  pattern: string;
  direction: 'bullish' | 'bearish' | 'neutral';
}

// 支撑/阻力水平位
export interface SRLevel {
  price: number;
  touches: number;
}

// 技术信号响应
export interface SignalsResult {
  code: string;
  current_price: number;
  patterns: PatternSignal[];
  support_resistance: {
    supports: SRLevel[];
    resistances: SRLevel[];
    current_price: number;
  };
  divergence: {
    top_divergence: boolean;
    bottom_divergence: boolean;
    detail: string;
    checked_bars: number;
  };
}

// 技术信号API
export const patternApi = {
  getSignals: (code: string, market: string = 'US', period: string = '3mo') =>
    api.get<SignalsResult>(`/stocks/${code}/signals`, { params: { market, period } }),
};

export default patternApi;
