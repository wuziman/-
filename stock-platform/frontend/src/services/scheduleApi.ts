import api from './api';

// 定时自动日报API（run-now需实时拉取全部自选股数据，超时放宽到60s）
export const scheduleApi = {
  getSchedule: () =>
    api.get('/report/schedule'),

  updateSchedule: (data: { enabled: boolean; hour: number; minute: number }) =>
    api.put('/report/schedule', data),

  runNow: () =>
    api.post('/report/run-now', null, { timeout: 60000 }),
};

export default scheduleApi;
