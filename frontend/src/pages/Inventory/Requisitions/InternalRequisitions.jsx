import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, DatePicker, Drawer, Form, Input, InputNumber, Select, Space, Table, Tag, Typography, message } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';
import { useSearchParams } from 'react-router-dom';

const { Title, Text } = Typography;

const STORAGE_KEY = 'twist_erp.requisitions.internal.v1';

const useProducts = () => {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const { data } = await api.get('/api/v1/inventory/products/');
        const list = Array.isArray(data) ? data : data?.results || [];
        setItems(list);
      } catch (_e) {
        setItems([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);
  return { items, loading };
};

const InternalRequisitions = ({ openNew = false, onCloseNew }) => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const [selectedCostCenter, setSelectedCostCenter] = useState(null);
  const [costCenters, setCostCenters] = useState([]);
  const [budgetLines, setBudgetLines] = useState([]);
  const { items: products, loading: productsLoading } = useProducts();
  const [searchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState([]);

  const loadRequisitions = async () => {
    try {
      setLoading(true);
      // Prefer backend API if available
      const { data } = await api.get('/api/v1/inventory/requisitions/internal/');
      const results = Array.isArray(data) ? data : data?.results || [];
      setList(results);
    } catch (_err) {
      // Fallback to local storage
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        setList(Array.isArray(parsed) ? parsed : []);
      } catch {
        setList([]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRequisitions(); }, [currentCompany?.id, statusFilter]);

  useEffect(() => {
    // Auto-open drawer when ?new=1
    if (searchParams.get('new') === '1') {
      setOpen(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (openNew) {
      setOpen(true);
    }
  }, [openNew]);

  // Load cost centers and budget lines when drawer opens
  useEffect(() => {
    const loadCc = async () => {
      try {
        const { data } = await api.get('/api/v1/budgets/cost-centers/');
        const list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
        setCostCenters(list.map(cc => ({ value: cc.id, label: `${cc.code || ''} ${cc.name}`.trim() })));
        const stored = localStorage.getItem('twist-default-cost-center');
        const found = list.find(cc => String(cc.id) === String(stored)) || list[0] || null;
        if (found) setSelectedCostCenter(found.id);
      } catch (e) {
        setCostCenters([]);
      }
    };
    const loadBl = async () => {
      try {
        const { data } = await api.get('/api/v1/budgets/lines/');
        const list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
        setBudgetLines(list);
      } catch (e) {
        setBudgetLines([]);
      }
    };
    if (open) {
      loadCc();
      loadBl();
    }
  }, [open]);

  const setDefaultCostCenter = (ccId) => {
    setSelectedCostCenter(ccId);
    try { localStorage.setItem('twist-default-cost-center', String(ccId)); } catch (_) {}
  };

  const findBudgetForProduct = (productId) => {
    const product = (products || []).find(p => String(p.id) === String(productId));
    if (!product || !selectedCostCenter) return null;
    const name = (product.name || '').toLowerCase();
    const matches = (budgetLines || []).filter(bl => {
      const itemName = (bl.item_name || '').toLowerCase();
      return itemName.includes(name);
    });
    return matches[0] || null;
  };

  const handleAction = async (record, action) => {
    try {
      await api.post(`/api/v1/inventory/requisitions/internal/${record.id}/${action}/`);
      message.success(`${action.charAt(0).toUpperCase() + action.slice(1)}d`);
      await loadRequisitions();
    } catch (e) {
      message.error(`Failed to ${action}`);
    }
  };

  const columns = [
    { title: 'Req No', dataIndex: 'req_no', key: 'req_no' },
    { title: 'Requested On', dataIndex: 'request_date', key: 'request_date', render: (v) => (v ? dayjs(v).format('YYYY-MM-DD') : '-') },
    { title: 'Needed By', dataIndex: 'needed_by', key: 'needed_by', render: (v) => (v ? dayjs(v).format('YYYY-MM-DD') : '-') },
    { title: 'Items', dataIndex: 'lines', key: 'lines', render: (lines) => (Array.isArray(lines) ? lines.length : 0) },
    { title: 'Purpose', dataIndex: 'purpose', key: 'purpose', ellipsis: true },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s) => <Tag color={s === 'SUBMITTED' ? 'blue' : s === 'APPROVED' ? 'green' : 'default'}>{s || 'DRAFT'}</Tag> },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status !== 'SUBMITTED' && (
            <Button size="small" onClick={() => handleAction(record, 'submit')}>Submit</Button>
          )}
          {record.status === 'SUBMITTED' && (
            <Button size="small" onClick={() => handleAction(record, 'approve')}>Approve</Button>
          )}
          {record.status !== 'CANCELLED' && (
            <Button size="small" danger onClick={() => handleAction(record, 'cancel')}>Cancel</Button>
          )}
        </Space>
      ),
    },
  ];

  const BudgetInfo = ({ productId, costCenterId }) => {
    const [info, setInfo] = useState({ qty: '', used: '', remaining: '' });
    useEffect(() => {
      let cancelled = false;
      const load = async () => {
        if (!productId || !costCenterId) { setInfo({ qty: '', used: '', remaining: '' }); return; }
        try {
          const { data } = await api.get('/api/v1/budgets/lines/', { params: { cost_center: costCenterId, product: productId } });
          const line = Array.isArray(data?.results) ? data.results[0] : Array.isArray(data) ? data[0] : null;
          if (!cancelled) {
            setInfo({
              qty: line?.qty_limit ?? '',
              used: line?.consumed_quantity ?? '',
              remaining: line?.remaining_quantity ?? line?.available_quantity ?? '',
            });
          }
        } catch (_e) {
          if (!cancelled) setInfo({ qty: '', used: '', remaining: '' });
        }
      };
      load();
      return () => { cancelled = true; };
    }, [productId, costCenterId]);
    return (
      <>
        <Form.Item label="Budget Qty"><Input disabled value={info.qty} /></Form.Item>
        <Form.Item label="Used Qty"><Input disabled value={info.used} /></Form.Item>
        <Form.Item label="Remaining Qty"><Input disabled value={info.remaining} /></Form.Item>
      </>
    );
  };

  const LineRow = ({ name, restField, remove }) => {
    const productId = Form.useWatch([name, 'item_id'], form);
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 120px 100px 240px 160px 160px 160px auto', columnGap: 8, alignItems: 'end', marginBottom: 8 }}>
        <Form.Item {...restField} name={[name, 'item_id']} label="Item" rules={[{ required: true, message: 'Select item' }]}>
          <Select
            showSearch
            filterOption={(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())}
            loading={productsLoading}
            placeholder="Select item"
            optionFilterProp="label"
            style={{ minWidth: 260 }}
            options={(products || []).map((p) => ({ value: p.id, label: `${p.code || p.sku || ''} ${p.name}` }))}
          />
        </Form.Item>
        <Form.Item {...restField} name={[name, 'quantity']} label="Qty" rules={[{ required: true, message: 'Qty' }]}>
          <InputNumber min={0.001} step={1} style={{ width: 120 }} />
        </Form.Item>
        <Form.Item {...restField} name={[name, 'uom']} label="UoM">
          <Input placeholder="EA" style={{ width: 100 }} />
        </Form.Item>
        <Form.Item {...restField} name={[name, 'notes']} label="Notes">
          <Input placeholder="Optional" style={{ width: 240 }} />
        </Form.Item>
        <BudgetInfo productId={productId} costCenterId={selectedCostCenter} />
        <Button
          aria-label="Remove line"
          type="text"
          danger
          shape="circle"
          icon={<CloseOutlined />}
          onClick={remove}
        />
      </div>
    );
  };

  const handleCreate = async (values) => {
    const payload = {
      req_no: values.req_no || undefined,
      request_date: values.request_date ? values.request_date.format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      needed_by: values.needed_by ? values.needed_by.format('YYYY-MM-DD') : null,
      warehouse: values.warehouse || null,
      purpose: values.purpose || '',
      status: 'SUBMITTED',
      lines: (values.lines || []).map((ln, idx) => ({
        line_no: idx + 1,
        item_id: ln.item_id,
        item_name: products.find((p) => String(p.id) === String(ln.item_id))?.name || '',
        quantity: Number(ln.quantity) || 0,
        uom: ln.uom || 'EA',
        notes: ln.notes || '',
      })),
    };

    try {
      setSubmitting(true);
      // Try backend first
      const { data } = await api.post('/api/v1/inventory/requisitions/internal/', payload);
      message.success('Requisition submitted');
      setOpen(false);
      form.resetFields();
      setList((prev) => [data, ...prev]);
    } catch (_err) {
      // Fallback: persist to local storage
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const existing = raw ? JSON.parse(raw) : [];
        const saved = [{ id: `local-${Date.now()}`, ...payload }, ...existing];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
        setList(saved);
        message.success('Saved locally (offline mode)');
        setOpen(false);
        form.resetFields();
      } catch {
        message.error('Unable to save requisition');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const filteredList = useMemo(() => {
    let rows = Array.isArray(list) ? list : [];
    if (statusFilter && statusFilter !== 'ALL') {
      rows = rows.filter((r) => (r.status || '').toUpperCase() === statusFilter);
    }
    if (Array.isArray(dateRange) && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
      const [start, end] = dateRange;
      rows = rows.filter((r) => {
        const d = r.request_date ? dayjs(r.request_date) : null;
        return d && d.isAfter(start.startOf('day')) && d.isBefore(end.endOf('day'));
      });
    }
    return rows;
  }, [list, statusFilter, dateRange]);

  const exportCsv = () => {
    const rows = filteredList.map((r) => ({
      number: r.requisition_number || r.req_no || '',
      date: r.request_date || '',
      needed_by: r.needed_by || '',
      status: r.status || '',
      items: Array.isArray(r.lines) ? r.lines.length : 0,
      purpose: r.purpose || '',
    }));
    const header = 'Number,Date,Needed By,Status,Items,Purpose\n';
    const body = rows.map((x) => `${x.number},${x.date},${x.needed_by},${x.status},${x.items},"${(x.purpose || '').replace(/"/g,'""')}"`).join('\n');
    const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'internal_requisitions.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <Title level={2}>Internal Requisitions</Title>
      <Text type="secondary">Request stock from internal warehouses for operational needs.</Text>
      <Card style={{ marginTop: 16 }}
        extra={(
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'ALL', label: 'All' },
                { value: 'DRAFT', label: 'Draft' },
                { value: 'SUBMITTED', label: 'Submitted' },
                { value: 'APPROVED', label: 'Approved' },
                { value: 'CANCELLED', label: 'Cancelled' },
              ]}
              style={{ width: 160 }}
            />
            <DatePicker.RangePicker onChange={setDateRange} />
            <Button onClick={exportCsv}>Export CSV</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Make Requisition</Button>
          </Space>
        )}
      >
        <Table rowKey={(r) => r.id || r.req_no} loading={loading} dataSource={filteredList} columns={columns} pagination={{ pageSize: 10 }} />
      </Card>

      <Drawer
        title="Create Internal Requisition"
        open={open}
        width={900}
        styles={{ body: { overflowX: 'auto' } }}
        onClose={() => {
          setOpen(false);
          if (onCloseNew) onCloseNew();
        }}
        destroyOnClose
      >
        <Form layout="vertical" form={form} onFinish={handleCreate} initialValues={{ request_date: dayjs(), lines: [{}, {}], _cc: selectedCostCenter }}>
          <Space size={16} style={{ display: 'flex', marginBottom: 8 }}>
            <Form.Item name="_cc" label="Cost Center" rules={[{ required: true }]} extra="Your default cost center is preselected; you can change it">
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="Select cost center"
                value={selectedCostCenter}
                onChange={(val) => setDefaultCostCenter(val)}
                options={costCenters}
                style={{ minWidth: 260 }}
              />
            </Form.Item>
          </Space>
          <Space style={{ display: 'flex' }} size={16} wrap>
            <Form.Item label="Request Date" name="request_date" rules={[{ required: true }]}>
              <DatePicker />
            </Form.Item>
            <Form.Item label="Needed By" name="needed_by">
              <DatePicker />
            </Form.Item>
            <Form.Item label="Warehouse" name="warehouse">
              <Input placeholder="e.g., Main WH" />
            </Form.Item>
            <Form.Item label="Purpose/Notes" name="purpose" style={{ minWidth: 300 }}>
              <Input.TextArea rows={2} placeholder="Optional" />
            </Form.Item>
          </Space>

          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <Card title="Items" size="small" extra={<Button onClick={() => add()}>Add Line</Button>}>
                {fields.map(({ key, name, ...restField }) => (
                  <LineRow key={key} name={name} restField={restField} remove={() => remove(name)} />
                ))}
              </Card>
            )}
          </Form.List>

          <Space style={{ marginTop: 16 }}>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={submitting}>Submit</Button>
          </Space>
        </Form>
      </Drawer>
    </div>
  );
};

export default InternalRequisitions;
