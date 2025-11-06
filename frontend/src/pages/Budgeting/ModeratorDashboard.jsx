import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Card, Col, DatePicker, Drawer, Form, Input, Modal, Row, Select, Space, Spin, Table, Tag, Tooltip, message } from 'antd';
import dayjs from 'dayjs';
import {
  fetchBudgets,
  fetchBudgetLines,
  fetchModeratorQueue,
  fetchModeratorReviewSummary,
  completeModeratorReview,
  addModeratorRemark,
  batchAddRemarks,
  batchSendBackForReview,
  batchApplyTemplateToCategory,
  fetchRemarkTemplates,
  fetchVarianceAudit,
  fetchLinePricePrediction,
  fetchLineConsumptionForecast,
  updateBudgetLine,
} from '../../services/budget';

const PROCUREMENT_OPTIONS = [
  { value: 'stock_item', label: 'Stock Item' },
  { value: 'service_item', label: 'Service / Expense' },
  { value: 'capex_item', label: 'Capex Item' },
];

const ModeratorDashboard = () => {
  const [loading, setLoading] = useState(false);
  const [budgets, setBudgets] = useState([]);
  const [selectedBudget, setSelectedBudget] = useState(null);
  const [lines, setLines] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [summary, setSummary] = useState(null);

  const [filters, setFilters] = useState({ category: 'ALL', procurement_class: 'ALL', variance: 'ALL', amount: 'ALL' });

  const [remarkModal, setRemarkModal] = useState(false);
  const [remarkText, setRemarkText] = useState('');
  const [remarkTemplate, setRemarkTemplate] = useState(null);

  const [holdModal, setHoldModal] = useState(false);
  const [holdReason, setHoldReason] = useState('');
  const [holdUntil, setHoldUntil] = useState(null);

  const [auditOpen, setAuditOpen] = useState(false);
  const [auditForLine, setAuditForLine] = useState(null);
  const [auditRows, setAuditRows] = useState([]);

  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiForLine, setAiForLine] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiInfo, setAiInfo] = useState(null);

  const loadBudgets = useCallback(async () => {
    setLoading(true);
    try {
      // Prefer moderator queue
      let rows = [];
      try {
        const mq = await fetchModeratorQueue();
        rows = Array.isArray(mq?.data) ? mq.data : [];
      } catch (_) {
        // ignore; will fallback below
      }
      // Fallback to budgets by status if queue empty or unavailable
      if (!Array.isArray(rows) || rows.length === 0) {
        try {
          const all = await fetchBudgets({ status: 'PENDING_MODERATOR_REVIEW' });
          rows = all?.data?.results || all?.data || [];
        } catch (e2) {
          message.error(e2?.response?.data?.detail || 'Failed to load moderator queue');
        }
      }
      setBudgets(rows || []);
      if ((rows || []).length && !selectedBudget) setSelectedBudget(rows[0].id);
    } finally {
      setLoading(false);
    }
  }, [selectedBudget]);

  const loadTemplates = useCallback(async () => {
    try {
      const { data } = await fetchRemarkTemplates();
      setTemplates(data?.results || data || []);
    } catch (_) {}
  }, []);

  const loadLines = useCallback(async () => {
    if (!selectedBudget) return;
    setLoading(true);
    try {
      const { data } = await fetchBudgetLines({ budget: selectedBudget, page_size: 1000 });
      const rows = data?.results || data || [];
      setLines(rows);
    } catch (e) {
      message.error('Failed to load budget lines');
    } finally {
      setLoading(false);
    }
  }, [selectedBudget]);

  const loadSummary = useCallback(async () => {
    if (!selectedBudget) return;
    try {
      const { data } = await fetchModeratorReviewSummary(selectedBudget);
      setSummary(data);
    } catch (_) {}
  }, [selectedBudget]);

  useEffect(() => { loadBudgets(); loadTemplates(); }, [loadBudgets, loadTemplates]);
  useEffect(() => { loadLines(); loadSummary(); }, [loadLines, loadSummary]);

  const categories = useMemo(() => ['ALL', ...Array.from(new Set((lines||[]).map(l => l.category).filter(Boolean)))], [lines]);

  const filtered = useMemo(() => {
    return (lines || []).filter((l) => {
      if (filters.category !== 'ALL' && l.category !== filters.category) return false;
      if (filters.procurement_class !== 'ALL' && l.procurement_class !== filters.procurement_class) return false;
      if (filters.variance === 'VARIANCE_ONLY') {
        const v = Number(l.value_variance || 0);
        if (v === 0) return false;
      }
      if (filters.amount === '>5000') {
        if (Number(l.value_limit || 0) <= 5000) return false;
      }
      if (filters.amount === '>10000') {
        if (Number(l.value_limit || 0) <= 10000) return false;
      }
      return true;
    });
  }, [lines, filters]);

  const doBatchRemark = async () => {
    const ids = selectedRowKeys;
    if (!ids?.length) return;
    try {
      if (remarkTemplate) {
        await batchAddRemarks({ budget_line_ids: ids, remark_text: remarkText || '', remark_template_id: remarkTemplate });
      } else {
        await batchAddRemarks({ budget_line_ids: ids, remark_text: remarkText || '' });
      }
      message.success('Remarks applied');
      setRemarkModal(false); setRemarkText(''); setRemarkTemplate(null);
      loadLines();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to apply remarks');
    }
  };

  const doBatchSendBack = async () => {
    const ids = selectedRowKeys;
    if (!ids?.length) return;
    try {
      await batchSendBackForReview({ budget_line_ids: ids, reason: remarkText || 'Please review' });
      message.success('Items sent back for review');
      setRemarkModal(false); setRemarkText('');
      loadLines();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to send back items');
    }
  };

  const doBatchHold = async () => {
    const ids = selectedRowKeys;
    if (!ids?.length) return;
    try {
      await Promise.all(ids.map((id) => updateBudgetLine(id, {
        is_held_for_review: true,
        held_reason: holdReason || 'Held for further review',
        held_until_date: holdUntil ? dayjs(holdUntil).toISOString() : null,
      })));
      message.success('Selected items held');
      setHoldModal(false); setHoldReason(''); setHoldUntil(null);
      loadLines();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to hold items');
    }
  };

  const columns = [
    { title: 'Item', dataIndex: 'item_name', key: 'item_name', render: (v, r) => <Space direction="vertical" size={0}><span>{v}</span><span style={{ color: '#999', fontSize: 12 }}>{r.item_code}</span></Space> },
    { title: 'Class', dataIndex: 'procurement_class', render: (v) => <Tag>{v}</Tag> },
    { title: 'Category', dataIndex: 'category' },
    { title: 'Value', dataIndex: 'value_limit', render: (v) => Number(v||0).toLocaleString() },
    { title: 'Variance', key: 'variance', render: (_, r) => {
      const v = Number(r.value_variance || 0);
      const color = v === 0 ? 'default' : (v > 0 ? 'red' : 'green');
      return <Tag color={color}>{v.toLocaleString()}</Tag>;
    }},
    { title: 'Flags', key: 'flags', render: (_, r) => (
      <Space size={4} wrap>
        {r.sent_back_for_review ? <Tag color="orange">Sent Back</Tag> : null}
        {r.is_held_for_review ? <Tag color="gold">Held</Tag> : null}
        {r.moderator_remarks ? <Tooltip title={r.moderator_remarks}><Tag color="blue">Remark</Tag></Tooltip> : null}
      </Space>
    )},
    { title: 'Actions', key: 'actions', render: (_, r) => (
      <Space>
        <Button size="small" onClick={async () => {
          try {
            await addModeratorRemark(r.id, { remark_text: 'Approved - Looks Good' });
            loadLines();
          } catch (e) { message.error('Failed'); }
        }}>OK</Button>
        <Button size="small" onClick={() => { setAuditForLine(r); setAuditOpen(true); }}>Audit</Button>
        <Button size="small" onClick={async () => {
          setAiForLine(r);
          setAiModalOpen(true);
          setAiLoading(true);
          try {
            const [pred, fc] = await Promise.all([
              fetchLinePricePrediction(r.id).catch(() => ({ data: null })),
              fetchLineConsumptionForecast(r.id).catch(() => ({ data: null })),
            ]);
            setAiInfo({ prediction: pred?.data || null, forecast: fc?.data || null });
          } catch (_) {
            setAiInfo(null);
          } finally {
            setAiLoading(false);
          }
        }}>Insights</Button>
      </Space>
    )},
  ];

  useEffect(() => {
    const run = async () => {
      if (!auditForLine) return;
      try {
        const { data } = await fetchVarianceAudit({ budget_line: auditForLine.id, limit: 100 });
        setAuditRows(data?.results || data || []);
      } catch (_) { setAuditRows([]); }
    };
    run();
  }, [auditForLine]);

  return (
    <>
    <Spin spinning={loading} tip="Loading moderator dashboard">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Row gutter={12} align="middle">
          <Col span={12}>
            <Space>
              <Select
                style={{ minWidth: 320 }}
                placeholder="Select budget"
                value={selectedBudget}
                onChange={(v) => { setSelectedBudget(v); setSelectedRowKeys([]); }}
                options={(budgets||[]).map((b) => ({ value: b.id, label: b.name || `Budget ${b.id}` }))}
              />
              <Select value={filters.category} onChange={(v) => setFilters({ ...filters, category: v })} options={categories.map((c) => ({ value: c, label: c }))} />
              <Select value={filters.procurement_class} onChange={(v) => setFilters({ ...filters, procurement_class: v })} options={[{ value: 'ALL', label: 'All Classes' }, ...PROCUREMENT_OPTIONS]} />
              <Select value={filters.variance} onChange={(v) => setFilters({ ...filters, variance: v })} options={[{ value: 'ALL', label: 'All Items' }, { value: 'VARIANCE_ONLY', label: 'Variance Only' }]} />
              <Select value={filters.amount} onChange={(v) => setFilters({ ...filters, amount: v })} options={[{ value: 'ALL', label: 'Any Amount' }, { value: '>5000', label: '> $5k' }, { value: '>10000', label: '> $10k' }]} />
            </Space>
          </Col>
          <Col span={12} style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setRemarkModal(true)}>Add Remark</Button>
              <Button onClick={doBatchSendBack}>Send Back</Button>
              <Button onClick={() => setHoldModal(true)}>Hold</Button>
              <Button type="primary" onClick={async () => { try { await completeModeratorReview(selectedBudget, {}); message.success('Marked as reviewed'); loadBudgets(); } catch (e) { message.error('Failed to complete review'); } }}>Mark Reviewed</Button>
            </Space>
          </Col>
        </Row>

        <Card>
          <Table
            rowKey="id"
            rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
            dataSource={filtered}
            columns={columns}
            pagination={{ pageSize: 12 }}
          />
        </Card>

        <Modal
          title="Add Remarks (Batch)"
          open={remarkModal}
          onCancel={() => { setRemarkModal(false); setRemarkText(''); setRemarkTemplate(null); }}
          onOk={doBatchRemark}
          okButtonProps={{ disabled: (!remarkText && !remarkTemplate) || !selectedRowKeys?.length }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.TextArea rows={3} placeholder="Remark text" value={remarkText} onChange={(e) => setRemarkText(e.target.value)} />
            <Select
              allowClear
              placeholder="Or choose template"
              value={remarkTemplate}
              onChange={setRemarkTemplate}
              options={(templates||[]).map((t) => ({ value: t.id, label: t.name }))}
            />
          </Space>
        </Modal>

        <Modal
          title="Hold Items"
          open={holdModal}
          onCancel={() => { setHoldModal(false); setHoldReason(''); setHoldUntil(null); }}
          onOk={doBatchHold}
          okButtonProps={{ disabled: !selectedRowKeys?.length }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input placeholder="Reason" value={holdReason} onChange={(e) => setHoldReason(e.target.value)} />
            <DatePicker showTime value={holdUntil ? dayjs(holdUntil) : null} onChange={(v) => setHoldUntil(v)} />
          </Space>
        </Modal>

        <Drawer
          title={`Variance Audit · ${auditForLine?.item_name || ''}`}
          open={auditOpen}
          width={640}
          onClose={() => { setAuditOpen(false); setAuditForLine(null); setAuditRows([]); }}
        >
          <Table
            rowKey="id"
            size="small"
            dataSource={auditRows}
            columns={[
              { title: 'When', dataIndex: 'created_at' },
              { title: 'Who', dataIndex: 'modified_by_display' },
              { title: 'Type', dataIndex: 'change_type' },
              { title: 'Qty Δ', dataIndex: 'qty_variance' },
              { title: 'Price Δ', dataIndex: 'price_variance' },
              { title: 'Value Δ', dataIndex: 'value_variance' },
              { title: 'Reason', dataIndex: 'modification_reason' },
            ]}
            pagination={{ pageSize: 10 }}
          />
        </Drawer>
      </Space>
    </Spin>
    
    <Modal
      title={aiForLine ? `AI Insights · ${aiForLine.item_name}` : 'AI Insights'}
      open={aiModalOpen}
      onCancel={() => { setAiModalOpen(false); setAiForLine(null); setAiInfo(null); }}
      footer={null}
    >
      <Spin spinning={aiLoading}>
        {aiInfo ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Card size="small" title="Price Prediction">
              {aiInfo.prediction ? (
                <Space direction="vertical" size={2}>
                  <div>Predicted: <strong>{aiInfo.prediction.predicted_price}</strong></div>
                  <div>Confidence: {aiInfo.prediction.confidence || 0}%</div>
                  {aiInfo.prediction.last_po_price ? (<div>Last PO: {aiInfo.prediction.last_po_price}</div>) : null}
                  {aiInfo.prediction.avg_price ? (<div>Avg: {aiInfo.prediction.avg_price}</div>) : null}
                  <div>Method: {aiInfo.prediction.method || '-'}</div>
                </Space>
              ) : 'No prediction available'}
            </Card>
            <Card size="small" title="Consumption Forecast">
              {aiInfo.forecast ? (
                <Space direction="vertical" size={2}>
                  <div>Projected: <strong>{aiInfo.forecast.projected_consumption_value}</strong></div>
                  <div>Confidence: {aiInfo.forecast.confidence || 0}%</div>
                  {aiInfo.forecast.will_exceed_budget ? <Tag color="red">May Exceed</Tag> : <Tag color="green">OK</Tag>}
                  <div>Method: {aiInfo.forecast.method || '-'}</div>
                </Space>
              ) : 'No forecast available'}
            </Card>
          </Space>
        ) : (
          <div>No insights available.</div>
        )}
      </Spin>
    </Modal>
    </>
  );
};

export default ModeratorDashboard;
