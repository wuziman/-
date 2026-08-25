import api from './api';
import type { ScheduleInfo } from '../types/api';

// 定时自动日报API（run-now需实时拉取全部自选股数据，超时放宽到60s）
export const scheduleApi = {
  getSchedule: () =>
    api.get<ScheduleInfo>('/report/schedule'),

  updateSchedule: (data: { enabled: boolean; hour: number; minute: number }) =>
    api.put<{ message?: string }>('/report/schedule', data),

  runNow: () =>
    api.post<ReportSendLike>('/report/run-now', null, { timeout: 60000 }),
};

interface ReportSendLike {
  sent: boolean;
  message?: string;
}

export default scheduleApi;
