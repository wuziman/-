import React, { useState, useEffect } from 'react';
import {
  Card, Button, Tag, Space, Alert, Modal, Input, message,
  Descriptions, Spin, Typography, Tooltip
} from 'antd';
import {
  FileTextOutlined, ReloadOutlined, SettingOutlined, ThunderboltOutlined
} from '@ant-design/icons';
import { aiPickApi, errDetail } from '../services/api';
import type { PickRecord, StatusInfo, XhsSummaryRow } from '../types/api';
import { colors } from '../theme/tokens';

const { TextArea } = Input;
const { Paragraph } = Typography;

const CONF_COLOR: Record<string, string> = { high: 'red', medium: 'orange', low: 'default' };
const CONF_LABEL: Record<string, string> = { high: '高确信', medium: '中等', low: '低' };
// antd 预设橙/绿标签的文字色对比度仅3.3~3.4:1（不达WCAG AA），覆盖为同色相深色文字（≥7:1）
const TAG_TEXT_FIX = {
  orange: { color: '#873800' },
  green: { color: '#135200' },
} as const;

const AIPick: React.FC = () => {
  const [status, setStatus] = useState<StatusInfo | null>(null);
  const [history, setHistory] = useState<PickRecord[]>([]);
  const [running, setRunning] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);

  // 小红书配置弹窗
  const [xhsModalVisible, setXhsModalVisible] = useState(false);
  const [cookieInput, setCookieInput] = useState('');
  const [bloggersInput, setBloggersInput] = useState('');
  const [savingXhs, setSavingXhs] = useState(false);
  const [refreshingXhs, setRefreshingXhs] = useState(false);

  // 博主观点总结
  const [summaries, setSummaries] = useState<XhsSummaryRow[]>([]);
  const [loadingSummaries, setLoadingSummaries] = useState(true);
  const [generatingSummaries, setGeneratingSummaries] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await aiPickApi.getStatus();
      setStatus(res.data);
    } catch {
      // 状态读取失败不阻塞页面
    }
  };

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await aiPickApi.getHistory(30);
      setHistory(res.data);
    } catch {
      message.error('历史记录加载失败');
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchSummaries = async () => {
    setLoadingSummaries(true);
    try {
      const res = await aiPickApi.getXhsSummaries();
      setSummaries(res.data);
    } catch {
      // 总结读取失败不阻塞页面
    } finally {
      setLoadingSummaries(false);
    }
  };

  const generateSummaries = async (silent: boolean) => {
    if (!status?.ai_configured) {
      if (!silent) message.warning('请先在 config/config.json 配置 ai_provider 再生成总结');
      return;
    }
    setGeneratingSummaries(true);
    try {
      const res = await aiPickApi.generateXhsSummaries();
      const ok = res.data.summaries?.length || 0;
      const fail = res.data.errors?.length || 0;
      message.success(`博主总结完成：${ok}位成功${fail ? `，${fail}位失败` : ''}`);
      await fetchSummaries();
    } catch (error) {
      const detail = errDetail(error, '博主总结生成失败');
      message.error(String(detail).slice(0, 120));
    } finally {
      setGeneratingSummaries(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchHistory();
    fetchSummaries();
  }, []);

  const handleRun = () => {
    if (!status?.ai_configured) {
      message.warning('请先在 config/config.json 配置 ai_provider（base_url/api_key/model）');
      return;
    }
    Modal.confirm({
      title: '运行AI选股？',
      content: '将拉取候选池行情与新闻、结合小红书内容调用大模型分析，耗时约1-3分钟，并消耗少量API额度。',
      okText: '开始分析',
      onOk: async () => {
        setRunning(true);
        try {
          const res = await aiPickApi.run();
          message.success(`AI选股完成：${res.data.picks.length}只入选`);
          await Promise.all([fetchStatus(), fetchHistory()]);
        } catch (error) {
          const detail = errDetail(error, 'AI选股失败');
          message.error(String(detail).slice(0, 120));
        } finally {
          setRunning(false);
        }
      }
    });
  };

  const openXhsModal = async () => {
    try {
      const res = await aiPickApi.getXhsConfig();
      setCookieInput(''); // 出于安全不回显已存Cookie，留空=保持不变
      setBloggersInput((res.data.bloggers || [])
        .map((b) => `${b.name}|${b.url}`).join('\n'));
      setXhsModalVisible(true);
    } catch {
      message.error('配置读取失败');
    }
  };

  const handleSaveXhs = async () => {
    const bloggers = bloggersInput
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, url] = line.split('|');
        return { name: (name || '').trim(), url: (url || '').trim() };
      })
      .filter((b) => b.url);

    if (bloggers.length === 0 && !cookieInput.trim()) {
      message.warning('请至少填写博主链接或Cookie');
      return;
    }
    setSavingXhs(true);
    try {
      await aiPickApi.saveXhsConfig({
        cookie: cookieInput.trim() ? cookieInput.trim() : undefined,
        bloggers,
      });
      message.success('小红书配置已保存');
      setXhsModalVisible(false);
      fetchStatus();
    } catch {
      message.error('保存失败');
    } finally {
      setSavingXhs(false);
    }
  };

  const handleRefreshXhs = async () => {
    setRefreshingXhs(true);
    try {
      const res = await aiPickApi.refreshXhs();
      const total = (res.data.bloggers || []).reduce((s, b) => s + (b.count || 0), 0);
      message.success(`抓取完成：${total}条笔记，新增${res.data.new_posts}条入库`);
      fetchStatus();
      generateSummaries(true);   // 抓取成功后自动生成博主总结（未配AI时静默跳过）
    } catch (error) {
      message.error(errDetail(error, '抓取失败'));
    } finally {
      setRefreshingXhs(false);
    }
  };

  const grouped = history.reduce<Record<string, PickRecord[]>>((acc, r) => {
        (acc[r.run_date] = acc[r.run_date] || []).push(r);
    return acc;
  }, {});

  return (
    <div>
      <h2>🤖 AI选股（Serenity供应链卡点思维 · 仅美股）</h2>

      {/* ===== 配置状态 ===== */}
      {status && !status.ai_configured && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          message="AI供应商未配置"
          description={
            <div style={{ fontSize: 13 }}>
              请编辑 <b>股票投资/config/config.json</b>，添加 ai_provider 字段（该文件不会提交到git）：
              <Paragraph copyable style={{ margin: '8px 0 0', fontSize: 12, background: colors.bgLight, padding: 8 }}>
                {`"ai_provider": {"base_url": "https://openrouter.ai/api/v1", "api_key": "你的key", "model": "厂商/模型ID"}`}
              </Paragraph>
            </div>
          }
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space size="large" wrap align="center">
          <Button
            type="primary"
            size="large"
            icon={<ThunderboltOutlined />}
            onClick={handleRun}
            loading={running}
            disabled={!status?.ai_configured}
          >
            {running ? 'AI分析中…（约1-3分钟）' : '开始AI选股'}
          </Button>
          <Descriptions column={1} size="small" style={{ flex: 1, minWidth: 320 }}>
            <Descriptions.Item label="AI模型">
              {status?.ai_configured
                ? <Tag color="green" style={TAG_TEXT_FIX.green}>{status.ai_model}</Tag>
                : <Tag color="red">未配置</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="小红书">
              <Space>
                <Tag color={status?.xhs_cookie_set ? 'green' : 'default'} style={status?.xhs_cookie_set ? TAG_TEXT_FIX.green : undefined}>
                  {status?.xhs_cookie_set ? 'Cookie已配' : '无Cookie'}
                </Tag>
                <span>{status?.bloggers?.length || 0}个博主 · 缓存{status?.cached_posts || 0}条</span>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="上次运行">
              {status?.last_run_date || '从未运行'}
            </Descriptions.Item>
          </Descriptions>
          <Space direction="vertical">
            <Button icon={<SettingOutlined />} onClick={openXhsModal}>小红书设置</Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefreshXhs}
              loading={refreshingXhs}
              disabled={!status?.xhs_cookie_set}
            >
              抓取最新帖子
            </Button>
          </Space>
        </Space>
        <div style={{ color: colors.textSecondary, fontSize: 12, marginTop: 12 }}>
          分析框架：产业链卡点 → 定价权 → 验证链 → 压力测试。候选池默认覆盖AI算力/半导体/光通信25只美股，
          可在config.json的ai_provider.universe字段自定义。输出仅供研究参考，不构成投资建议。
        </div>
      </Card>

      {/* ===== 博主观点总结 ===== */}
      <Card
        title="📝 博主观点总结"
        style={{ marginBottom: 16 }}
        extra={
          <Button
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => generateSummaries(false)}
            loading={generatingSummaries}
            disabled={!status?.ai_configured}
          >
            {generatingSummaries ? '总结生成中…' : '重新总结'}
          </Button>
        }
      >
        {loadingSummaries ? (
          <div style={{ textAlign: 'center', padding: 30 }}><Spin /></div>
        ) : summaries.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: colors.textSecondary }}>
            还没有博主总结——抓取最新帖子后会自动生成每位博主的观点总结
          </div>
        ) : (
          summaries.map((s) => (
            <Card
              key={s.blogger_name}
              type="inner"
              title={
                <Space>
                  <b>{s.blogger_name}</b>
                  <Tag>{s.posts_count}条帖子</Tag>
                  {(s.period_start || s.period_end) && (
                    <span style={{ color: colors.textSecondary, fontSize: 12 }}>{s.period_start} ~ {s.period_end}</span>
                  )}
                </Space>
              }
              style={{ marginBottom: 12 }}
            >
              <Paragraph style={{ marginBottom: 4 }}>{s.summary_text}</Paragraph>
              <div style={{ color: colors.textSecondary, fontSize: 12 }}>
                生成于 {s.created_at ? s.created_at.replace('T', ' ').slice(0, 16) : '--'}
              </div>
            </Card>
          ))
        )}
      </Card>

      {/* ===== 历史结果 ===== */}
      {loadingHistory ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin /></div>
      ) : Object.keys(grouped).length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: 40, color: colors.textSecondary }}>
            还没有选股记录——点击上方「开始AI选股」跑第一次分析
          </div>
        </Card>
      ) : (
        Object.entries(grouped).map(([runDate, picks]) => {
          const commentary = picks.find((p) => p.market_commentary)?.market_commentary;
          return (
            <Card
              key={runDate}
              title={`📋 ${runDate} 选股结果`}
              style={{ marginBottom: 16 }}
              extra={<Tooltip title="按rank排序"><Tag>{picks.length}只</Tag></Tooltip>}
            >
              {commentary && (
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message={`板块判断：${commentary}`}
                />
              )}
              {picks.map((p) => (
                <Card
                  key={p.id}
                  type="inner"
                  title={
                    <Space>
                      <b>#{p.rank} {p.stock_code}</b>
                      <span>{p.stock_name}</span>
                      <Tag
                        color={CONF_COLOR[p.confidence]}
                        style={CONF_COLOR[p.confidence] === 'orange' ? TAG_TEXT_FIX.orange : undefined}
                      >
                        {CONF_LABEL[p.confidence]}
                      </Tag>
                      {p.price_at_pick != null && <span style={{ color: colors.textSecondary }}>@${p.price_at_pick}</span>}
                    </Space>
                  }
                  style={{ marginBottom: 12 }}
                >
                  <p><b>💡 核心论点：</b>{p.thesis}</p>
                  <p><b>🔗 卡点：</b>{p.bottlenecks}</p>
                  <p><b>⚠️ 反方压力测试：</b>{p.risks}</p>
                  <p style={{ marginBottom: 0 }}><b>🚀 催化剂：</b>{p.catalysts}</p>
                </Card>
              ))}
            </Card>
          );
        })
      )}

      {/* ===== 小红书设置弹窗 ===== */}
      <Modal
        title="小红书接入设置"
        open={xhsModalVisible}
        onCancel={() => setXhsModalVisible(false)}
        onOk={handleSaveXhs}
        confirmLoading={savingXhs}
        okText="保存"
        width="92%"
        style={{ maxWidth: 560 }}
      >
        <p style={{ fontSize: 13 }}>
          博主列表（每行一条，格式：<code>显示名|主页链接</code>）：
        </p>
        <TextArea
          rows={4}
          placeholder={'半导体老张|https://www.xiaohongshu.com/user/profile/xxxxxxx'}
          value={bloggersInput}
          onChange={(e) => setBloggersInput(e.target.value)}
        />
        <p style={{ fontSize: 13, marginTop: 16 }}>
          登录Cookie（浏览器打开小红书 → F12 → Network → 任一请求 → 复制Cookie请求头的值；留空则保持原值。约30天过期需更新）：
        </p>
        <TextArea
          rows={3}
          placeholder="粘贴Cookie…"
          value={cookieInput}
          onChange={(e) => setCookieInput(e.target.value)}
        />
        <Alert
          type="info"
          style={{ marginTop: 12, fontSize: 12 }}
          message="非官方接口：小红书反爬升级可能导致抓取失效，届时重新更新Cookie或改用其他方案。仅抓取公开笔记标题/简介作参考输入。"
        />
      </Modal>
    </div>
  );
};

export default AIPick;
