import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Card, Table, Space, Button, message, Select, Row, Col, Statistic, Modal, Form, Input, InputNumber, Tag } from 'antd';
import api from '../../services/api';
import dayjs from 'dayjs';
import {
  fetchDeclaredBudgetsEntry,
  fetchPermittedCostCentersEntry,
  fetchEntrySummary,
  fetchEntryLines,
  getEntryPrice,
  addBudgetItem,
  submitEntry,
  openEntry,
  deleteBudgetLine,
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
  const [newRow, setNewRow] = useState({ item_code: '', item_name: '', quantity: 1, manual_unit_price: 0 });
  const [itemOptions, setItemOptions] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [filters, setFilters] = useState({ code: '', name: '' });
  // Ref to item code select for quick focus after add
  const itemCodeRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const [declRes, ccRes] = await Promise.all([
        fetchDeclaredBudgetsEntry({ cost_center: selectedCC }),
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

  // load item options (budget item codes) for dropdowns
  useEffect(() => {
    const run = async () => {
      try {
        const res = await api.get('/api/v1/budgets/item-codes/?page_size=1000');
        const list = Array.isArray(res.data) ? res.data : (res.data?.results || []);
        setItemOptions(list.map((x) => ({ code: x.code, name: x.name, standard_price: Number(x.standard_price ?? 0) })));
      } catch (_) {
        setItemOptions([]);
      }
    };
    run();
  }, []);

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
              options={(declared || []).map((b) => {
                const name = (b.display_name || b.name || '').trim();
                const period = b.period_start && b.period_end ? `${b.period_start} → ${b.period_end}` : '';
                const label = name ? `${name}${period ? ` (${period})` : ''}` : (period || `Budget ${b.id}`);
                return { value: b.id, label };
              })}
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
            <Col><Statistic title="Budget Items No." value={summary.budget_items || 0} /></Col>
            <Col><Statistic title="Budget Value" value={Number(summary.value || 0)} precision={2} /></Col>
            <Col><Statistic title="Used Value" value={Number(summary.used || 0)} precision={2} /></Col>
            <Col><Statistic title="Remaining Value" value={Number(summary.remaining || 0)} precision={2} /></Col>
          </Row>
        </Col>
      </Row>

      <Space style={{ marginBottom: 8 }}>
        <Button onClick={() => message.success('Saved as draft')} disabled={!selectedBudget || !selectedCC}>Save as Draft</Button>
        <Button type="primary" onClick={handleSubmit} disabled={!selectedBudget || !selectedCC}>Submit</Button>
        {selectedRowKeys && selectedRowKeys.length > 0 ? (
          <Button
            danger
            onClick={async () => {
              try {
                const deletable = (lines || []).filter((r) => selectedRowKeys.includes(r.id) && r.can_delete);
                if (deletable.length === 0) {
                  message.warning('No selected rows can be deleted');
                  return;
                }
                await Promise.all(deletable.map((r) => deleteBudgetLine(r.id)));
                message.success(`Deleted ${deletable.length} row(s)`);
                setSelectedRowKeys([]);
                const [sum, lin] = await Promise.all([
                  fetchEntrySummary(selectedBudget),
                  fetchEntryLines(selectedBudget, selectedCC),
                ]);
                setSummary(sum.data || summary);
                setCcBudget(lin.data?.cc_budget || null);
                setLines(lin.data?.lines || []);
              } catch (e) {
                message.error(e?.response?.data?.detail || 'Failed to delete selected rows');
              }
            }}
          >
            Delete Selected
          </Button>
        ) : null}
        {/* Open Entry button removed: entry opens automatically by window */}
      </Space>

      {/* Inline entry now merged into main table as the first row */}

      <Table
        rowKey="id"
        loading={loading}
        dataSource={(selectedBudget && selectedCC) ? ([{ id: '__new__', _isNew: true, ...newRow }, ...lines]) : lines}
        pagination={{ pageSize: 10 }}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys.filter((k) => k !== '__new__')),
          getCheckboxProps: (record) => ({ disabled: record._isNew || !record.can_delete }),
        }}
        columns={[
          {
            title: 'Item Code',
            dataIndex: 'item_code',
            filterDropdown: ({ confirm, clearFilters }) => (
              <div style={{ padding: 8 }}>
                <Input
                  placeholder="Search code"
                  value={filters.code}
                  onChange={(e) => setFilters((f) => ({ ...f, code: e.target.value }))}
                  onPressEnter={() => confirm()}
                  style={{ width: 188, marginBottom: 8, display: 'block' }}
                />
                <Space>
                  <Button type="primary" size="small" onClick={() => confirm()}>Filter</Button>
                  <Button size="small" onClick={() => { setFilters((f) => ({ ...f, code: '' })); clearFilters && clearFilters(); }}>Reset</Button>
                </Space>
              </div>
            ),
            onFilter: () => true,
            render: (v, record) => record._isNew ? (
              <Select
                ref={itemCodeRef}
                showSearch
                style={{ width: '100%' }}
                placeholder="Select item code"
                value={newRow.budget_item_code || undefined}
                optionFilterProp="label"
                optionLabelProp="label"
                onChange={async (val) => {
                  const found = itemOptions.find((o) => o.code === val);
                  // Optimistically set price from master data, then refine using policy endpoint
                  setNewRow((r) => ({
                    ...r,
                    item_code: val,
                    item_name: found?.name || r.budget_item_name,
                    manual_unit_price: typeof found?.standard_price === 'number' ? found.standard_price : r.manual_unit_price,
                  }));
                  if (val) {
                    try {
                      const { data } = await getEntryPrice(val);
                      const p = Number(data?.unit_price);
                      setNewRow((r) => ({ ...r, manual_unit_price: (isFinite(p) && p > 0) ? p : r.manual_unit_price }));
                    } catch (_) {
                      // keep optimistic standard price if policy lookup fails
                    }
                  }
                }}
                options={(itemOptions || []).map((o) => ({ value: o.code, label: `${o.code} - ${o.name}` }))}
              />
            ) : (
              <span>
                {record.budget_item_code}
                {record.budget_item_name ? ` - ${record.budget_item_name}` : ''}
              </span>
            )
          },
          {
            title: 'Category',
            dataIndex: 'item_category_name',
            render: (v, record) => (record._isNew ? '-' : (v || record.budget_item_category_name || record.category_name || record.category || '-')),
          },
          {
            title: 'Sub-Category',
            dataIndex: 'sub_category_name',
            render: (v, record) => (record._isNew ? '-' : (v || '-')),
          },
          {
            title: 'Quantity',
            dataIndex: 'qty_limit',
            render: (v, record) => record._isNew ? (
              <InputNumber
                min={0}
                step={0.01}
                value={newRow.quantity}
                onChange={(val) => setNewRow((r) => ({ ...r, quantity: Number(val || 0) }))}
                onKeyDown={async (e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    // invoke the same add action as the button
                    try {
                      if (!newRow.budget_item_code || !newRow.quantity) {
                        message.error('Item code and quantity are required');
                        return;
                      }
                      if (!(Number(newRow.manual_unit_price) > 0)) {
                        message.error('Unit price must be greater than 0');
                        return;
                      }
                      await addBudgetItem({
                        budget: selectedBudget,
                        cost_center: selectedCC,
                        item_code: newRow.budget_item_code,
                        item_name: newRow.budget_item_name,
                        quantity: newRow.quantity,
                        manual_unit_price: newRow.manual_unit_price,
                      });
                      message.success('Item added');
                      setNewRow({ item_code: '', item_name: '', quantity: 1, manual_unit_price: 0 });
                      const [sum, lin] = await Promise.all([
                        fetchEntrySummary(selectedBudget),
                        fetchEntryLines(selectedBudget, selectedCC),
                      ]);
                      setSummary(sum.data || summary);
                      setCcBudget(lin.data?.cc_budget || null);
                      setLines(lin.data?.lines || []);
                      // Focus back to item code select for faster entry loop
                      setTimeout(() => {
                        try { itemCodeRef.current?.focus?.(); } catch (_) {}
                      }, 0);
                    } catch (err) {
                      message.error(err?.response?.data?.detail || 'Failed to add item');
                    }
                  }
                }}
                style={{ width: '100%' }}
              />
            ) : v
          },
          {
            title: 'Unit Price',
            dataIndex: 'unit_price',
            render: (v, record) => record._isNew ? (
              <InputNumber
                min={0.01}
                step={0.01}
                value={newRow.manual_unit_price}
                onChange={(val) => setNewRow((r) => ({ ...r, manual_unit_price: Number(val || 0) }))}
                style={{ width: '100%' }}
              />
            ) : (typeof v !== 'undefined' && v !== null ? v : (record && typeof record.manual_unit_price !== 'undefined' && record.manual_unit_price !== null ? record.manual_unit_price : record.standard_price))
          },
          {
            title: 'Value',
            dataIndex: 'value_limit',
            render: (v, record) => record._isNew ? (
              <span>{(Number(newRow.quantity || 0) * Number(newRow.manual_unit_price || 0)).toFixed(2)}</span>
            ) : v
          },
          {
            title: 'Status',
            dataIndex: 'status',
            render: (v) => {
              let statusText = (v || 'draft').replace('_', ' ');
              let color = 'default';
              if (v === 'approved') color = 'green';
              if (v === 'final_approved') {
                statusText = 'final approved';
                color = 'blue';
              }
              if (v === 'rejected') color = 'red';
              if (v === 'submitted') color = 'gold';
              if (v === 'needs_review') color = 'orange';
              return <Tag color={color}>{statusText}</Tag>;
            },
          },
          {
            title: 'Action',
            key: 'action',
            render: (v, record) => record._isNew ? (
              <Button
                type="primary"
                onClick={async () => {
                  try {
                    if (!newRow.budget_item_code || !newRow.quantity) {
                      message.error('Item code and quantity are required');
                      return;
                    }
                    if (!(Number(newRow.manual_unit_price) > 0)) {
                      message.error('Unit price must be greater than 0');
                      return;
                    }
                    await addBudgetItem({
                      budget: selectedBudget,
                      cost_center: selectedCC,
                      item_code: newRow.budget_item_code,
                      item_name: newRow.budget_item_name,
                      quantity: newRow.quantity,
                      manual_unit_price: newRow.manual_unit_price,
                    });
                    message.success('Item added');
                    setNewRow({ item_code: '', item_name: '', quantity: 1, manual_unit_price: 0 });
                    const [sum, lin] = await Promise.all([
                      fetchEntrySummary(selectedBudget),
                      fetchEntryLines(selectedBudget, selectedCC),
                    ]);
                    setSummary(sum.data || summary);
                    setCcBudget(lin.data?.cc_budget || null);
                    setLines(lin.data?.lines || []);
                  } catch (e) {
                    message.error(e?.response?.data?.detail || 'Failed to add item');
                  }
                }}
              >
                Add
              </Button>
            ) : (
              record && record.can_delete ? (
                <Button
                  danger
                  size="small"
                  onClick={async () => {
                    try {
                      await deleteBudgetLine(record.id);
                      message.success('Row deleted');
                      const [sum, lin] = await Promise.all([
                        fetchEntrySummary(selectedBudget),
                        fetchEntryLines(selectedBudget, selectedCC),
                      ]);
                      setSummary(sum.data || summary);
                      setCcBudget(lin.data?.cc_budget || null);
                      setLines(lin.data?.lines || []);
                    } catch (e) {
                      message.error(e?.response?.data?.detail || 'Failed to delete row');
                    }
                  }}
                >
                  Delete
                </Button>
              ) : null
            )
          }
        ]}
      />

      {/* Retain modal for fallback, can be removed later */}
      <Modal
        title="Add Budget Item"
        open={addOpen}
        destroyOnHidden
        forceRender
        onCancel={() => { setAddOpen(false); form.resetFields(); }}
        onOk={async () => {
          try {
            const v = await form.validateFields();
            await addBudgetItem({
              budget: selectedBudget,
              cost_center: selectedCC,
              item_code: v.budget_item_code,
              item_name: v.budget_item_name,
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
          {/* Item Name hidden per request */}
          <Form.Item label="Quantity" name="quantity" rules={[{ required: true }] }>
            <Input type="number" min={0} step={0.01} />
          </Form.Item>
          <Form.Item label="Unit Price (auto / manual)" name="manual_unit_price" rules={[{ validator: (_, v) => (v && Number(v) > 0 ? Promise.resolve() : Promise.reject(new Error('Unit price must be greater than 0'))) }]}>
            <Input type="number" min={0.01} step={0.01} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default BudgetEntry;



