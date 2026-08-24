import axios from 'axios';

// 独立axios实例（不依赖api.ts）
const api = axios.create({
  baseURL: '/api',
  timeout: 60000, // run-now需实时拉取全部自选股数据，超时放宽
});

// 定时自动日报API
export const scheduleApi = {
  getSchedule: () =>
    api.get('/report/schedule'),

  updateSchedule: (data: { enabled: boolean; hour: number; minute: number }) =>
    api.put('/report/schedule', data),

  runNow: () =>
    api.post('/report/run-now'),
};

export default api;
