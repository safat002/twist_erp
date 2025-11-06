import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Space, Button, message, Select, Row, Col, Statistic, Modal, Form, Input } from 'antd';
import dayjs from 'dayjs';
import {
  fetchDeclaredBudgetsEntry,
  fetchPermittedCostCentersEntry,
  fetchEntrySummary,
  fetchEntryLines,
  getEntryPrice,
  addBudgetItem,
  submitEntry,
} from '../../services/budget';
import EntryPeriodStatus from '../../components/Budgeting/EntryPeriodStatus';

const BudgetEntry = () => {
  const [loading, setLoading] = useState(true);
  const [declared, setDeclared] = useState([]);
  const [selectedBudget, setSelectedBudget] = useState(null);
  const [costCenters, setCostCenters] = useState([]);
  const [selectedCC, setSelectedCC] = useState(null);
  const [summary, setSummary] = useState({ items: 0, value: '0.00', used: '0.00', remaining: '0.00' });
  const [ccBudget, setCcBudget] = useState(null);
  const [lines, setLines] = useState([]);
  const [addOpen, setAddOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      const [declRes, ccRes] = await Promise.all([
        fetchDeclaredBudgetsEntry(),
        fetchPermittedCostCentersEntry(),
      ]);
      const dec = declRes.data || [];
      setDeclared(dec);
      const ccs = ccRes.data || [];
      setCostCenters(ccs);
      if (!selectedBudget && dec.length) setSelectedBudget(dec[0].id);
      if (!selectedCC && ccs.length) setSelectedCC(ccs[0].id);
    } catch (e) {
      message.error('Failed to load entry data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // load summary whenever declared changes
  useEffect(() => {
    const run = async () => {
      if (!selectedBudget) return;
      try {
        const { data } = await fetchEntrySummary(selectedBudget);
        setSummary(data || { items: 0, value: '0.00', used: '0.00', remaining: '0.00' });
      } catch (_) {}
    };
    run();
  }, [selectedBudget]);

  // load lines whenever declared or CC changes
  useEffect(() => {
    const run = async () => {
      if (!selectedBudget || !selectedCC) return;
      try {
        const { data } = await fetchEntryLines(selectedBudget, selectedCC);
        setCcBudget(data?.cc_budget || null);
        setLines(data?.lines || []);
      } catch (e) {
        setCcBudget(null);
        setLines([]);
      }
    };
    run();
  }, [selectedBudget, selectedCC]);

  const handleSubmit = async () => {
    try {
      if (!selectedBudget || !selectedCC) return;
      await submitEntry({ budget: selectedBudget, cost_center: selectedCC });
      message.success('Submitted to Cost Center Owner');
      // refresh lines & summary
      const [sum, lin] = await Promise.all([
        fetchEntrySummary(selectedBudget),
        fetchEntryLines(selectedBudget, selectedCC),
      ]);
      setSummary(sum.data || summary);
      setCcBudget(lin.data?.cc_budget || null);
      setLines(lin.data?.lines || []);
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to submit');
    }
  };

  return (
    <Card title="Budget Entry">
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={10}>
          <Space>
            <Select
              style={{ minWidth: 320 }}
              placeholder="Select declared budget"
              value={selectedBudget}
              onChange={(v) => setSelectedBudget(v)}
              options={(declared || []).map((b) => ({ value: b.id, label: `${b.name} (${b.period_start} → ${b.period_end})` }))}
            />
            <Select
              style={{ minWidth: 240 }}
              placeholder="Select cost center"
              value={selectedCC}
              onChange={(v) => setSelectedCC(v)}
              options={(costCenters || []).map((c) => ({ value: c.id, label: `${c.code} - ${c.name || ''}` }))}
            />
          </Space>
        </Col>
        <Col span={14}>
          <Row gutter={12} justify="end">
            <Col><Statistic title="Budget Items No." value={summary.items || 0} /></Col>
            <Col><Statistic title="Budget Value" value={Number(summary.value || 0)} precision={2} /></Col>
            <Col><Statistic title="Used Value" value={Number(summary.used || 0)} precision={2} /></Col>
            <Col><Statistic title="Remaining Value" value={Number(summary.remaining || 0)} precision={2} /></Col>
          </Row>
        </Col>
      </Row>

      <Space style={{ marginBottom: 8 }}>
        <Button type="primary" onClick={() => setAddOpen(true)} disabled={!selectedBudget || !selectedCC}>Add Budget Item</Button>
        <Button onClick={handleSubmit} disabled={!selectedBudget || !selectedCC}>Submit This Cost Center</Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={lines}
        pagination={{ pageSize: 10 }}
        columns={[
          { title: 'Item Code', dataIndex: 'item_code' },
          { title: 'Item Name', dataIndex: 'item_name' },
          { title: 'Quantity', dataIndex: 'qty_limit' },
          { title: 'Unit Price', dataIndex: 'standard_price' },
          { title: 'Value', dataIndex: 'value_limit' },
        ]}
      />

      <Modal
        title="Add Budget Item"
        open={addOpen}
        destroyOnClose
        onCancel={() => { setAddOpen(false); form.resetFields(); }}
        onOk={async () => {
          try {
            const v = await form.validateFields();
            await addBudgetItem({
              budget: selectedBudget,
              cost_center: selectedCC,
              item_code: v.item_code,
              item_name: v.item_name,
              quantity: v.quantity,
              manual_unit_price: v.manual_unit_price,
            });
            message.success('Item added');
            setAddOpen(false); form.resetFields();
            const [sum, lin] = await Promise.all([
              fetchEntrySummary(selectedBudget),
              fetchEntryLines(selectedBudget, selectedCC),
            ]);
            setSummary(sum.data || summary);
            setCcBudget(lin.data?.cc_budget || null);
            setLines(lin.data?.lines || []);
          } catch (e) {
            if (e?.errorFields) return;
            message.error(e?.response?.data?.detail || 'Failed to add item');
          }
        }}
      >
        <Form layout="vertical" form={form} initialValues={{ quantity: 1 }}>
          <Form.Item label="Item Code" name="item_code" rules={[{ required: true }]}>
            <Input placeholder="Enter item code" onBlur={async (e) => {
              const code = e.target.value;
              if (!code) return;
              try {
                const { data } = await getEntryPrice(code);
                form.setFieldsValue({ manual_unit_price: Number(data?.unit_price || 0) });
              } catch (_) {}
            }} />
          </Form.Item>
          <Form.Item label="Item Name" name="item_name">
            <Input placeholder="Optional item name" />
          </Form.Item>
          <Form.Item label="Quantity" name="quantity" rules={[{ required: true }] }>
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
          <Form.Item label="Unit Price (auto / manual)" name="manual_unit_price">
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default BudgetEntry;
