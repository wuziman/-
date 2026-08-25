import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Spin, message, Button, Modal, Alert, Space, Switch, TimePicker, Popconfirm } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  StockOutlined,
  FileTextOutlined,
  SendOutlined,
  SaveOutlined,
  ThunderboltOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import echarts from '../services/echarts';
import { portfolioApi, stockApi, reportApi, errDetail } from '../services/api';
import { scheduleApi } from '../services/scheduleApi';
import { colors } from '../theme/tokens';

interface PositionSummary {
  total_positions: number;
  total_value: number;
  total_cost: number;
  total_profit: number;
  total_profit_pct: number;
  total_capital: number;
  cash_pct: number | null;
  warnings: Array<{ level: string; message: string }>;
}

const Home: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [watchlist, setWatchlist] = useState<any[]>([]);
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportText, setReportText] = useState('');
  const [reportLoading, setReportLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [reportMeta, setReportMeta] = useState<{ sent: boolean; message: string; char_count?: number } | null>(null);
  const [loadErrors, setLoadErrors] = useState<{ summary?: boolean; watchlist?: boolean }>({});
  // 自选股行情（渐进填充，失败显示'--'）
  const [wlQuotes, setWlQuotes] = useState<Record<string, { price: number | null; change_pct: number | null }>>({});
  const navigate = useNavigate();

  // ---------- 定时自动日报 ----------
  const [schedEnabled, setSchedEnabled] = useState(false);
  const [schedTime, setSchedTime] = useState<dayjs.Dayjs | null>(dayjs('17:30', 'HH:mm'));
  const [lastSentDate, setLastSentDate] = useState<string | null>(null);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [runningNow, setRunningNow] = useState(false);

  // ---------- 财报日历 ----------
  const [earningsItems, setEarningsItems] = useState<Array<{
    stock_code: string;
    stock_name: string;
    market: string;
    earnings_date: string;
    days_away: number;
  }>>([]);

  const fetchData = async () => {
    setLoading(true);
    // 分区加载：任一接口失败只标记对应分区，避免把失败渲染成全零仪表盘
    const [summaryRes, watchlistRes] = await Promise.allSettled([
      portfolioApi.getSummary(),
      stockApi.getWatchlist()
    ]);
    const failed: { summary?: boolean; watchlist?: boolean } = {};
    if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value.data);
    else failed.summary = true;
    if (watchlistRes.status === 'fulfilled') setWatchlist(watchlistRes.value.data);
    else failed.watchlist = true;
    setLoadErrors(failed);
    setLoading(false);
  };

  // ---------- 定时自动日报 ----------
  const fetchSchedule = async () => {
    try {
      const res = await scheduleApi.getSchedule();
      setSchedEnabled(res.data.enabled);
      setSchedTime(dayjs().hour(res.data.hour).minute(res.data.minute).second(0));
      setLastSentDate(res.data.last_sent_date);
    } catch {
      // 调度配置读取失败不影响仪表盘主数据
    }
  };

  const fetchQuotes = () => {
    stockApi.getWatchlistQuotes()
      .then((res) => {
        const map: Record<string, { price: number | null; change_pct: number | null }> = {};
        for (const q of res.data) map[q.stock_code] = q;
        setWlQuotes(map);
      })
      .catch(() => {}); // 行情失败表格显示'--'，不影响列表
  };

  useEffect(() => {
    fetchData();
    fetchSchedule();
    fetchQuotes();
    // 财报日历加载失败不影响仪表盘主数据（美股逐只查询较慢，静默降级）
    stockApi.getEarningsCalendar()
      .then((res) => setEarningsItems(res.data.items || []))
      .catch(() => {});
  }, []);

  const handleRemoveWatch = async (id: number) => {
    try {
      await stockApi.removeFromWatchlist(id);
      message.success('已从自选股删除');
      fetchData();
      fetchQuotes();
    } catch (error) {
      message.error(errDetail(error, '删除失败'));
    }
  };

  const handleSaveSchedule = async () => {
    if (!schedTime) {
      message.warning('请选择推送时间');
      return;
    }
    setSavingSchedule(true);
    try {
      await scheduleApi.updateSchedule({
        enabled: schedEnabled,
        hour: schedTime.hour(),
        minute: schedTime.minute(),
      });
      message.success(
        schedEnabled
          ? `已保存：工作日 ${schedTime.format('HH:mm')} 自动推送日报`
          : '已保存：自动推送已关闭'
      );
    } catch (error) {
      message.error(errDetail(error, '保存失败'));
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleRunNow = () => {
    Modal.confirm({
      title: '立即推送日报到企业微信',
      content: '将立即生成当前自选股日报并推送（无视定时开关），确认执行？',
      okText: '立即推送',
      cancelText: '取消',
      onOk: async () => {
        setRunningNow(true);
        try {
          const res = await scheduleApi.runNow();
          if (res.data.sent) {
            message.success('✅ 日报已推送到企业微信');
            fetchSchedule();
          } else {
            message.error(res.data.message || '推送失败');
          }
        } catch (error) {
          message.error(errDetail(error, '推送失败'));
        } finally {
          setRunningNow(false);
        }
      }
    });
  };

  // ---------- 每日报告 ----------
  const handlePreviewReport = async () => {
    setReportLoading(true);
    setReportModalVisible(true);
    try {
      const res = await reportApi.preview();
      setReportText(res.data.report);
      setReportMeta({ sent: false, message: '预览模式（未推送）', char_count: res.data.char_count });
    } catch (error) {
      const detail = errDetail(error, '生成失败');
      message.error(detail);
      setReportText(`生成失败：${detail}`);
      setReportMeta(null);
      setReportModalVisible(false);
    } finally {
      setReportLoading(false);
    }
  };

  const handleSendReport = async () => {
    Modal.confirm({
      title: '推送日报到企业微信',
      content: '将把当前自选股日报推送到配置的企业微信群，确认发送？',
      okText: '确认推送',
      cancelText: '取消',
      onOk: async () => {
        setSending(true);
        try {
          const res = await reportApi.send(false);
          if (res.data.sent) {
            message.success('✅ 日报已推送到企业微信');
            setReportText(res.data.report);
            setReportMeta({ sent: true, message: '已推送到企业微信', char_count: res.data.char_count });
            setReportModalVisible(true);
          } else {
            message.error(res.data.message || '推送失败');
          }
        } catch (error) {
          const detail = errDetail(error, '推送失败');
          message.error(detail);
        } finally {
          setSending(false);
        }
      }
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  const getPortfolioChartOption = () => {
    if (!summary) return {};
    // 资产分布 = 持仓市值 + 现金。此前把"浮动亏损"（已含在市值内）与市值并列，
    // 既双重计数又误用绿色切片，与全页盈亏语义冲突
    const capital = summary.total_capital || 0;
    const data: Array<{ value: number; name: string; itemStyle: { color: string } }> = [
      { value: Math.max(summary.total_value, 0), name: '持仓市值', itemStyle: { color: colors.primary } },
    ];
    if (capital > 0) {
      data.push({ value: Math.max(capital - summary.total_value, 0), name: '现金', itemStyle: { color: colors.chartNeutral } });
    }
    return {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        name: '资产分布',
        type: 'pie',
        radius: '50%',
        data,
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
        }
      }]
    };
  };

  return (
    <div>
      <Row justify="space-between" align="middle">
        <h2>📊 仪表盘</h2>
        <Space>
          <Button icon={<FileTextOutlined />} onClick={handlePreviewReport} loading={reportLoading}>
            预览日报
          </Button>
          <Button type="primary" icon={<SendOutlined />} onClick={handleSendReport} loading={sending}>
            推送微信日报
          </Button>
        </Space>
      </Row>

      {loadErrors.summary && (
        <Alert
          type="error"
          showIcon
          style={{ marginTop: 16 }}
          message="持仓统计加载失败——下方总览数字暂不可用，不代表真实持仓状况"
          action={<Button size="small" danger onClick={fetchData}>重新加载</Button>}
        />
      )}
      {!loadErrors.summary && (
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={12} sm={12} lg={6}>
          <Card><Statistic title="持仓数量" value={summary?.total_positions || 0} prefix={<StockOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <Card><Statistic title="持仓市值" value={summary?.total_value || 0} precision={2} prefix="$" /></Card>
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总盈亏"
              value={summary?.total_profit || 0}
              precision={2}
              prefix="$"
              suffix={(summary?.total_profit || 0) > 0 ? <ArrowUpOutlined style={{ color: colors.profit }} /> : (summary?.total_profit || 0) < 0 ? <ArrowDownOutlined style={{ color: colors.loss }} /> : undefined}
              valueStyle={{ color: (summary?.total_profit || 0) > 0 ? colors.profit : (summary?.total_profit || 0) < 0 ? colors.loss : colors.textSecondary }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <Card>
            <Statistic
              title="收益率"
              value={summary?.total_profit_pct || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: (summary?.total_profit_pct || 0) > 0 ? colors.profit : (summary?.total_profit_pct || 0) < 0 ? colors.loss : colors.textSecondary }}
            />
          </Card>
        </Col>
      </Row>
      )}

      {/* 风控预警摘要 */}
      {summary?.warnings && summary.warnings.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 16 }}
          message={`⚠️ 有${summary.warnings.length}项仓位风控预警，前往「持仓管理」查看详情`}
        />
      )}

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12}>
          <Card title="📈 资产分布" style={{ height: 420 }}>
            {summary && summary.total_positions > 0 ? (
              <ReactEChartsCore echarts={echarts} option={getPortfolioChartOption()} style={{ height: 320 }} />
            ) : (
              <div style={{ textAlign: 'center', padding: 50, color: colors.textSecondary }}>暂无持仓数据</div>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12}>
          <Card
            title="⭐ 自选股"
            style={{ height: 420 }}
            extra={<span style={{ fontSize: 12, color: colors.textSecondary }}>点击行进入分析</span>}
          >
            {loadErrors.watchlist ? (
              <Alert
                type="error"
                showIcon
                message="自选股列表加载失败"
                action={<Button size="small" danger onClick={fetchData}>重新加载</Button>}
              />
            ) : (
            <Table
              dataSource={watchlist}
              rowKey="id"
              pagination={false}
              size="small"
              scroll={{ y: 280 }}
              onRow={(r: any) => ({
                onClick: () => navigate(`/analysis?code=${r.stock_code}&name=${encodeURIComponent(r.stock_name)}&market=${r.market || 'US'}`),
                style: { cursor: 'pointer' },
              })}
              columns={[
                { title: '代码', dataIndex: 'stock_code', key: 'stock_code' },
                { title: '名称', dataIndex: 'stock_name', key: 'stock_name' },
                {
                  title: '市场', dataIndex: 'market', key: 'market',
                  render: (market: string) => (
                    <Tag color={market === 'A' ? 'red' : 'blue'}>{market === 'A' ? 'A股' : '美股'}</Tag>
                  )
                },
                {
                  title: '现价', key: 'price', width: 80,
                  render: (_: unknown, r: any) => {
                    const p = wlQuotes[r.stock_code]?.price;
                    return p != null ? `$${Number(p).toFixed(2)}` : <span style={{ color: colors.textSecondary }}>--</span>;
                  }
                },
                {
                  title: '涨跌', key: 'chg', width: 80,
                  render: (_: unknown, r: any) => {
                    const c = wlQuotes[r.stock_code]?.change_pct;
                    if (c == null) return <span style={{ color: colors.textSecondary }}>--</span>;
                    const v = Number(c);
                    return (
                      <span style={{ color: v > 0 ? colors.profit : v < 0 ? colors.loss : colors.textSecondary }}>
                        {v > 0 ? '+' : ''}{v.toFixed(2)}%
                      </span>
                    );
                  }
                },
                {
                  title: '', key: 'op', width: 50,
                  render: (_: unknown, r: any) => (
                    <Popconfirm title="从自选股删除？" onConfirm={() => handleRemoveWatch(r.id)}>
                      <Button type="text" size="small" danger aria-label="删除自选股" icon={<DeleteOutlined />} />
                    </Popconfirm>
                  )
                }
              ]}
            />
            )}
          </Card>
        </Col>
      </Row>

      {/* 财报日历 */}
      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="📅 自选股财报日历">
            {earningsItems.length > 0 ? (
              <Space size={[24, 12]} wrap>
                {earningsItems.map((e) => (
                  <Tag
                    key={e.stock_code}
                    color={e.days_away <= 7 ? 'red' : e.days_away <= 14 ? 'orange' : 'default'}
                    style={{ fontSize: 13, padding: '4px 10px' }}
                  >
                    <b>{e.stock_code} {e.stock_name}</b>
                    {'  '}财报：{e.earnings_date}
                    （{e.days_away === 0 ? '今天' : `${e.days_away}天后`}）
                  </Tag>
                ))}
              </Space>
            ) : (
              <span style={{ color: colors.textSecondary, fontSize: 13 }}>
                近30天暂无可确认的财报日期（A股数据源常缺财报日历，仅美股可查）
              </span>
            )}
          </Card>
        </Col>
      </Row>

      {/* 定时自动日报 */}
      <Row style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title="⏰ 自动日报"
            extra={<Tag color={schedEnabled ? 'green' : 'default'}>{schedEnabled ? '已启用' : '未启用'}</Tag>}
          >
            <Space size="large" wrap align="center">
              <Space>
                <span>启用定时推送</span>
                <Switch checked={schedEnabled} onChange={setSchedEnabled} />
              </Space>
              <Space>
                <span>推送时间</span>
                <TimePicker
                  format="HH:mm"
                  value={schedTime}
                  onChange={setSchedTime}
                  disabled={!schedEnabled}
                  allowClear={false}
                />
              </Space>
              <Button icon={<SaveOutlined />} onClick={handleSaveSchedule} loading={savingSchedule}>
                保存设置
              </Button>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleRunNow} loading={runningNow}>
                立即推送
              </Button>
            </Space>
            <div style={{ color: colors.textSecondary, marginTop: 12, fontSize: 13 }}>
              工作日按设定时间自动生成日报并推送到企业微信（后台每30分钟检查一次，当日仅发送一次）。
              最近发送日期：<b>{lastSentDate || '从未发送'}</b>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 日报弹窗 */}
      <Modal
        title="📋 每日报告"
        open={reportModalVisible}
        onCancel={() => setReportModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setReportModalVisible(false)}>关闭</Button>,
          <Button key="send" type="primary" icon={<SendOutlined />}
                  loading={sending}
                  onClick={() => { setReportModalVisible(false); handleSendReport(); }}>
            推送到企业微信
          </Button>
        ]}
        width="92%"
        style={{ maxWidth: 640 }}
      >
        {reportMeta && (
          <Alert
            style={{ marginBottom: 12 }}
            type={reportMeta.sent ? 'success' : 'info'}
            message={`${reportMeta.message}${reportMeta.char_count ? ` | ${reportMeta.char_count}字节` : ''}`}
          />
        )}
        <pre style={{
          whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7,
          background: colors.bgSecondary, padding: 16, borderRadius: 8, maxHeight: 480, overflow: 'auto'
        }}>
          {reportText}
        </pre>
      </Modal>
    </div>
  );
};

export default Home;
