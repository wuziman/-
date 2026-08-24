import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, InputNumber, DatePicker, Tag, Space, Statistic, Row, Col, message, Popconfirm, Alert, Tabs, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ThunderboltFilled, WarningFilled, SettingOutlined } from '@ant-design/icons';
import { portfolioApi } from '../services/api';
import dayjs from 'dayjs';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import echarts from '../services/echarts';
import { colors } from '../theme/tokens';

interface Position {
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

interface PositionSummary {
  total_positions: number;
  total_value: number;
  total_cost: number;
  total_profit: number;
  total_profit_pct: number;
  total_capital: number;
  cash_pct: number | null;
  warnings: Array<{
    level: 'error' | 'warning' | 'info';
    code: string;
    name: string;
    weight: number;
    message: string;
  }>;
}

const Portfolio: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState<Position[]>([]);
  const [history, setHistory] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PositionSummary | null>(null);
  const [capitalInput, setCapitalInput] = useState<number | null>(null);
  const [capitalSaving, setCapitalSaving] = useState(false);

  const [sellModalVisible, setSellModalVisible] = useState(false);
  const [sellingPosition, setSellingPosition] = useState<Position | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  const [activeTab, setActiveTab] = useState<string>('holding');
  const [sellForm] = Form.useForm();
  const [form] = Form.useForm();

  // ---------- 组合净值曲线与回撤 ----------
  const [curve, setCurve] = useState<Array<{ date: string; value: number }>>([]);
  const [ddStats, setDdStats] = useState<{
    current_drawdown_pct: number;
    max_drawdown_pct: number;
    peak_value: number;
  } | null>(null);

  useEffect(() => {
    fetchData();
    // 净值曲线加载失败不影响持仓主数据
    portfolioApi.getEquityCurve()
      .then((res) => {
        setCurve(res.data.curve || []);
        setDdStats(res.data);
      })
      .catch(() => {});
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [positionsRes, historyRes, summaryRes, capitalRes] = await Promise.all([
        portfolioApi.getPositions(),
        portfolioApi.getHistory(),
        portfolioApi.getSummary(),
        portfolioApi.getTotalCapital()
      ]);
      setPositions(positionsRes.data);
      setHistory(historyRes.data);
      setSummary(summaryRes.data);
      const cap = capitalRes.data.total_capital || 0;
      setCapitalInput(cap || null);
    } catch (error) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  // ---------- 止损止盈触发检测 ----------
  const stopAlerts = positions.filter(p =>
    p.stop_loss && p.current_price && p.current_price <= p.stop_loss
  );
  const tpAlerts = positions.filter(p =>
    p.take_profit && p.current_price && p.current_price >= p.take_profit
  );

  const handleSaveCapital = async () => {
    if (capitalInput === null || capitalInput <= 0) {
      message.warning('请输入有效的总资金');
      return;
    }
    setCapitalSaving(true);
    try {
      await portfolioApi.setTotalCapital(capitalInput);
      message.success('总资金已保存');
      fetchData();
    } catch {
      message.error('保存失败');
    } finally {
      setCapitalSaving(false);
    }
  };

  // ---------- 卖出 ----------
  const openSellModal = (record: Position) => {
    setSellingPosition(record);
    sellForm.setFieldsValue({
      sell_price: record.current_price ?? record.buy_price,
      sell_date: dayjs()
    });
    setSellModalVisible(true);
  };

  const handleSellSubmit = async () => {
    if (!sellingPosition) return;
    try {
      const values = await sellForm.validateFields();
      const res = await portfolioApi.sellPosition(sellingPosition.id, {
        sell_price: values.sell_price,
        sell_date: values.sell_date.format('YYYY-MM-DD')
      });
      message.success(`卖出成功！已实现盈亏 ${res.data.realized_pnl >= 0 ? '+' : ''}$${res.data.realized_pnl}（${res.data.realized_pnl_pct}%），持有${res.data.holding_days}天`);
      setSellModalVisible(false);
      fetchData();
    } catch (error: any) {
      if (error.errorFields) return;
      message.error('卖出失败');
    }
  };

  const handleAdd = () => {
    setEditingPosition(null);
    form.resetFields();
    setEditModalVisible(true);
  };

  // ---------- 修改持仓：复用添加弹窗，代码/名称锁定不可改 ----------
  const handleEdit = (record: Position) => {
    setEditingPosition(record);
    form.setFieldsValue({
      stock_code: record.stock_code,
      stock_name: record.stock_name,
      buy_price: record.buy_price,
      quantity: record.quantity,
      buy_date: dayjs(record.buy_date),
      stop_loss: record.stop_loss,
      take_profit: record.take_profit,
    });
    setEditModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await portfolioApi.deletePosition(id);
      message.success('删除成功');
      fetchData();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingPosition) {
        await portfolioApi.updatePosition(editingPosition.id, {
          buy_price: values.buy_price,
          quantity: values.quantity,
          buy_date: values.buy_date.format('YYYY-MM-DD'),
          stop_loss: values.stop_loss ?? null,   // 清空=清除该价位
          take_profit: values.take_profit ?? null,
        });
        message.success('修改成功');
      } else {
        const data = {
          ...values,
          buy_date: values.buy_date.format('YYYY-MM-DD'),
          market: values.stock_code.match(/^\d/) ? 'A' : 'US'
        };
        await portfolioApi.addPosition(data);
        message.success('添加成功');
      }
      setEditModalVisible(false);
      fetchData();
    } catch (error: any) {
      if (error.errorFields) return;
      message.error('操作失败');
    }
  };

  // ---------- 表格列 ----------
  const holdingColumns = [
    { title: '代码', dataIndex: 'stock_code', key: 'stock_code', width: 90 },
    { title: '名称', dataIndex: 'stock_name', key: 'stock_name', width: 110 },
    {
      title: '市场', dataIndex: 'market', key: 'market', width: 70,
      render: (m: string) => <Tag color={m === 'A' ? 'red' : 'blue'}>{m === 'A' ? 'A股' : '美股'}</Tag>
    },
    { title: '买入价', dataIndex: 'buy_price', key: 'buy_price', width: 90, render: (p: number) => `$${p.toFixed(2)}` },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 70 },
    {
      title: '现价', dataIndex: 'current_price', key: 'current_price', width: 90,
      render: (p: number | null) => p ? `$${p.toFixed(2)}` : '-'
    },
    {
      title: '浮动盈亏', dataIndex: 'profit_loss', key: 'profit_loss', width: 120,
      render: (profit: number | null, r: Position) => {
        if (profit === null) return '-';
        return (
          <span style={{ color: profit >= 0 ? colors.profit : colors.loss, fontWeight: 'bold' }}>
            {profit >= 0 ? '+' : ''}${profit.toFixed(2)} ({r.profit_loss_pct?.toFixed(2)}%)
          </span>
        );
      }
    },
    {
      title: '持有天数', dataIndex: 'holding_days', key: 'holding_days', width: 80,
      render: (d: number | null) => d !== null ? `${d}天` : '-'
    },
    {
      title: '止损/止盈', key: 'levels', width: 140,
      render: (_: any, r: Position) => (
        <Space size={4}>
          <Tag color={r.current_price && r.stop_loss && r.current_price <= r.stop_loss ? 'red' : 'default'}>
            损{r.stop_loss ? `$${r.stop_loss}` : '-'}
          </Tag>
          <Tag color={r.current_price && r.take_profit && r.current_price >= r.take_profit ? 'green' : 'default'}>
            盈{r.take_profit ? `$${r.take_profit}` : '-'}
          </Tag>
        </Space>
      )
    },
    {
      title: '操作', key: 'action', width: 170,
      render: (_: any, r: Position) => (
        <Space>
          <Tooltip title="修改买入价/数量/止损止盈">
            <Button size="small" aria-label="修改持仓" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          </Tooltip>
          <Tooltip title="卖出">
            <Button type="primary" size="small" danger icon={<ThunderboltFilled />}
                    onClick={() => openSellModal(r)}>
              卖出
            </Button>
          </Tooltip>
          <Popconfirm title="确定删除该记录吗？" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" size="small" danger aria-label="删除持仓" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ];

  const historyColumns = [
    { title: '代码', dataIndex: 'stock_code', key: 'stock_code', width: 90 },
    { title: '名称', dataIndex: 'stock_name', key: 'stock_name', width: 110 },
    { title: '买入价', dataIndex: 'buy_price', key: 'buy_price', width: 90, render: (p: number) => `$${p.toFixed(2)}` },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 70 },
    { title: '卖出价', dataIndex: 'sell_price', key: 'sell_price', width: 90, render: (p: number | null) => p ? `$${p.toFixed(2)}` : '-' },
    { title: '买入日', dataIndex: 'buy_date', key: 'buy_date', width: 100, render: (d: string) => d?.slice(0, 10) },
    { title: '卖出日', dataIndex: 'sell_date', key: 'sell_date', width: 100, render: (d: string | null) => d?.slice(0, 10) || '-' },
    { title: '持有天数', dataIndex: 'holding_days', key: 'hd', width: 80, render: (d: number | null) => d !== null && d !== undefined ? `${d}天` : '-' },
    {
      title: '已实现盈亏', dataIndex: 'realized_pnl', key: 'rp', width: 130,
      render: (pnl: number | null, r: Position) => {
        if (pnl === null) return '-';
        return (
          <span style={{ color: pnl >= 0 ? colors.profit : colors.loss, fontWeight: 'bold' }}>
            {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)} ({r.realized_pnl_pct?.toFixed(2)}%)
          </span>
        );
      }
    },
    {
      title: '操作', key: 'action', width: 70,
      render: (_: any, r: Position) => (
        <Popconfirm title="删除该历史记录？" onConfirm={() => handleDelete(r.id)}>
          <Button type="link" size="small" danger aria-label="删除历史记录" icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ];

  return (
    <div>
      <h2>💼 持仓管理</h2>

      {/* ===== 止损止盈触发警报 ===== */}
      {stopAlerts.length > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 8 }}
          message={`⛔ 止损触发（${stopAlerts.length}只）`}
          description={
            <div>
              {stopAlerts.map(a => (
                <div key={a.id}>
                  <b>{a.stock_name}({a.stock_code})</b>：现价${a.current_price} 已跌破止损位${a.stop_loss}
                  ，当前浮亏{a.profit_loss_pct}% —— 严格执行止损纪律！
                </div>
              ))}
            </div>
          }
        />
      )}
      {tpAlerts.length > 0 && (
        <Alert
          type="success"
          showIcon
          style={{ marginBottom: 8 }}
          message={`🎯 止盈达成（${tpAlerts.length}只）`}
          description={
            <div>
              {tpAlerts.map(a => (
                <div key={a.id}>
                  <b>{a.stock_name}({a.stock_code})</b>：现价${a.current_price} 已达止盈位${a.take_profit}
                  ，当前盈利+{a.profit_loss_pct}% —— 考虑分批止盈落袋
                </div>
              ))}
            </div>
          }
        />
      )}

      {/* ===== 仓位集中度预警 ===== */}
      {summary?.warnings && summary.warnings.length > 0 && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningFilled />}
          style={{ marginBottom: 8 }}
          message={`⚠️ 仓位风控预警（${summary.warnings.length}项）`}
          description={
            <div>
              {summary.warnings.map((w, i) => <div key={i}>• {w.message}</div>)}
            </div>
          }
        />
      )}

      {/* ===== 总览统计 ===== */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} md={8} lg={4}>
          <Card><Statistic title="持仓数量" value={summary?.total_positions || 0} /></Card>
        </Col>
        <Col xs={12} md={8} lg={5}>
          <Card><Statistic title="持仓市值" value={summary?.total_value || 0} precision={2} prefix="$" /></Card>
        </Col>
        <Col xs={12} md={8} lg={5}>
          <Card>
            <Statistic
              title="浮动盈亏"
              value={summary?.total_profit || 0} precision={2} prefix="$"
              valueStyle={{ color: (summary?.total_profit || 0) >= 0 ? colors.profit : colors.loss }}
            />
          </Card>
        </Col>
        <Col xs={12} md={8} lg={5}>
          <Card>
            <Statistic
              title="收益率"
              value={summary?.total_profit_pct || 0} precision={2} suffix="%"
              valueStyle={{ color: (summary?.total_profit_pct || 0) >= 0 ? colors.profit : colors.loss }}
            />
          </Card>
        </Col>
        <Col xs={12} md={8} lg={5}>
          <Card>
            <Statistic
              title="现金比例"
              value={summary?.cash_pct ?? '—'}
              precision={summary?.cash_pct != null ? 1 : undefined}
              suffix={summary?.cash_pct != null ? '%' : ''}
              valueStyle={{
                color: summary?.cash_pct == null ? undefined :
                  summary.cash_pct < 15 ? colors.loss : summary.cash_pct > 25 ? colors.warning : colors.profit
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* ===== 组合净值曲线（每日快照） ===== */}
      <Card
        title="📈 组合净值曲线"
        style={{ marginBottom: 16 }}
        extra={
          ddStats && ddStats.max_drawdown_pct > 0 ? (
            <Space size={16}>
              <span style={{ fontSize: 13 }}>
                历史峰值 <b>${ddStats.peak_value?.toLocaleString()}</b>
              </span>
              <span style={{ fontSize: 13 }}>
                当前回撤{' '}
                <b style={{ color: ddStats.current_drawdown_pct >= 20 ? colors.loss : colors.profit }}>
                  -{ddStats.current_drawdown_pct}%
                </b>
                {' '}（历史最大 -{ddStats.max_drawdown_pct}%）
              </span>
            </Space>
          ) : null
        }
      >
        {curve.length > 1 ? (
          <>
            {ddStats && ddStats.current_drawdown_pct >= 20 && (
              <Alert
                type="error"
                showIcon
                style={{ marginBottom: 8 }}
                message={`⛔ 当前回撤 -${ddStats.current_drawdown_pct}%，已超过20%组合风控线，请审视整体仓位`}
              />
            )}
            <ReactEChartsCore
              echarts={echarts}
              option={{
                tooltip: { trigger: 'axis' },
                grid: { left: 70, right: 20, top: 20, bottom: 30 },
                xAxis: { type: 'category', data: curve.map(p => p.date) },
                yAxis: { type: 'value', scale: true },
                series: [{
                  name: '组合市值',
                  type: 'line',
                  data: curve.map(p => p.value),
                  smooth: true,
                  showSymbol: false,
                  lineStyle: { color: colors.primary, width: 2 },
                  areaStyle: { color: colors.primary, opacity: 0.12 },
                }],
              }}
              style={{ height: 260 }}
            />
            <div style={{ fontSize: 12, color: colors.textSecondary }}>
              快照由后台监控任务在每个交易时段自动写入（同日取最新值）
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: 30, color: colors.textSecondary }}>
            暂无快照数据——后台监控任务会在交易时段自动记录每日组合市值，累积几天后这里会出现曲线
          </div>
        )}
      </Card>

      <Card
        title="持仓明细"
        extra={
          <Space>
            <Tooltip title="设置总资金后启用单票40%上限与现金比例预警">
              <InputNumber
                prefix={<SettingOutlined />}
                placeholder="总资金"
                min={0}
                step={10000}
                value={capitalInput}
                onChange={(v) => setCapitalInput(v)}
                formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={value => Number(value?.replace(/\$\s?|(,*)/g, '') || 0) as any}
                style={{ width: 150 }}
              />
            </Tooltip>
            <Button onClick={handleSaveCapital} loading={capitalSaving}>保存</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>添加持仓</Button>
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'holding',
              label: `当前持仓 (${positions.length})`,
              children: (
                <Table
                  columns={holdingColumns}
                  dataSource={positions}
                  rowKey="id"
                  loading={loading}
                  pagination={false}
                  scroll={{ x: 1100 }}
                  locale={{ emptyText: '暂无持仓，点击右上角添加' }}
                />
              )
            },
            {
              key: 'history',
              label: `历史交易 (${history.length})`,
              children: (
                <Table
                  columns={historyColumns}
                  dataSource={history}
                  rowKey="id"
                  loading={loading}
                  pagination={false}
                  scroll={{ x: 1100 }}
                  locale={{ emptyText: '暂无历史交易' }}
                />
              )
            }
          ]}
        />
      </Card>

      {/* ===== 卖出弹窗 ===== */}
      <Modal
        title={`卖出 ${sellingPosition?.stock_name || ''} (${sellingPosition?.stock_code || ''})`}
        open={sellModalVisible}
        onOk={handleSellSubmit}
        onCancel={() => setSellModalVisible(false)}
        okText="确认卖出"
        width="92%"
        style={{ maxWidth: 520 }}
      >
        {sellingPosition && (
          <Alert
            type="info"
            style={{ marginBottom: 16 }}
            message={`买入价$${sellingPosition.buy_price} × ${sellingPosition.quantity}股 | 现价$${sellingPosition.current_price ?? '-'} | 浮动盈亏${sellingPosition.profit_loss_pct ?? '-'}%`}
          />
        )}
        <Form form={sellForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="sell_price" label="卖出价格" rules={[{ required: true, message: '请输入卖出价格' }]}>
                <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="sell_date" label="卖出日期" rules={[{ required: true, message: '请选择日期' }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* ===== 添加/修改持仓弹窗 ===== */}
      <Modal
        title={editingPosition ? `修改持仓 ${editingPosition.stock_name} (${editingPosition.stock_code})` : '添加持仓'}
        open={editModalVisible}
        onOk={handleSubmit}
        onCancel={() => setEditModalVisible(false)}
        width="92%"
        style={{ maxWidth: 600 }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="stock_code" label="股票代码" rules={[{ required: true, message: '请输入股票代码' }]}>
            <Input placeholder="如：AAPL, MU, 000001" disabled={!!editingPosition} />
          </Form.Item>
          <Form.Item name="stock_name" label="股票名称" rules={[{ required: true, message: '请输入股票名称' }]}>
            <Input placeholder="如：苹果, 美光科技" disabled={!!editingPosition} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="buy_price" label="买入价格" rules={[{ required: true, message: '请输入买入价格' }]}>
                <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="quantity" label="数量" rules={[{ required: true, message: '请输入数量' }]}>
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="buy_date" label="买入日期" rules={[{ required: true, message: '请选择买入日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="stop_loss" label="止损位"><InputNumber style={{ width: '100%' }} min={0} step={0.01} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="take_profit" label="止盈位"><InputNumber style={{ width: '100%' }} min={0} step={0.01} /></Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default Portfolio;
