import React, { useEffect, useState } from 'react';
import { Button, Card, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, message, Checkbox } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { useNavigate, useSearchParams } from 'react-router-dom';

const { Title, Text } = Typography;

const STORAGE_KEY = 'twist_erp.requisitions.purchase.v1';

const useBudgetItems = () => {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState([]);
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const { data } = await api.get('/api/v1/budgets/item-codes/');
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

const PurchaseRequisitions = ({ openNew = false, onCloseNew }) => {
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formCreate] = Form.useForm();
  const [formConvert] = Form.useForm();
  const [convertOpen, setConvertOpen] = useState(false);
  const [converting, setConverting] = useState(false);
  const [convertTarget, setConvertTarget] = useState(null);
  const [ccOptions, setCcOptions] = useState([]);
  const [blOptions, setBlOptions] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState([]);
  const { items: budgetItems, loading: budgetItemsLoading } = useBudgetItems();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedCostCenter, setSelectedCostCenter] = useState(null);
  const [budgetLines, setBudgetLines] = useState([]);

  const loadRequisitions = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter && statusFilter !== 'ALL') params.status = statusFilter;
      const { data } = await api.get('/api/v1/procurement/requisitions/', { params });
      const results = Array.isArray(data) ? data : data?.results || [];
      setList(results);
    } catch (_err) {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        setList(raw ? JSON.parse(raw) : []);
      } catch {
        setList([]);
      }
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { loadRequisitions(); }, [statusFilter]);
  useEffect(() => { if (searchParams.get('new') === '1') setOpen(true); }, [searchParams]);
  useEffect(() => { if (openNew) setOpen(true); }, [openNew]);

  // Load budget lines and cost centers when create drawer opens
  useEffect(() => {
    const loadBl = async () => {
      try {
        const { data } = await api.get('/api/v1/budgets/lines/');
        const list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
        setBudgetLines(list);
      } catch (e) {
        setBudgetLines([]);
      }
    };
    const loadCc = async () => {
      try {
        const { data } = await api.get('/api/v1/budgets/cost-centers/');
        const list = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
        setCcOptions(list.map((cc) => ({ value: cc.id, label: `${cc.code || ''} ${cc.name}` })));
        const stored = localStorage.getItem('twist-default-cost-center');
        const found = list.find(cc => String(cc.id) === String(stored)) || list[0] || null;
        if (found) setSelectedCostCenter(found.id);
      } catch (e) {}
    };
    if (open) {
      loadBl();
      loadCc();
    }
  }, [open]);

  const loadCostCenters = async () => {
    try {
      const { data } = await api.get('/api/v1/budgets/cost-centers/');
      const list = Array.isArray(data) ? data : data?.results || [];
      setCcOptions(list.map((cc) => ({ value: cc.id, label: `${cc.code || ''} ${cc.name}` })));
    } catch (_e) {
      setCcOptions([]);
    }
  };

  const loadBudgetLines = async (costCenterId) => {
    try {
      const { data } = await api.get('/api/v1/budgets/lines/', { params: { cost_center: costCenterId } });
      const list = Array.isArray(data) ? data : data?.results || [];
      setBlOptions(list.map((bl) => ({ value: bl.id, label: `${bl.product_name || bl.reference_id || bl.id}` })));
    } catch (_e) {
      setBlOptions([]);
    }
  };

  const openConvert = async (record) => {
    setConvertTarget(record);
    setConvertOpen(true);
    await loadCostCenters();
  };

  const columns = [
    { title: 'PR No', dataIndex: 'requisition_number', key: 'requisition_number', render: (_v, r) => r.requisition_number || r.req_no || '-' },
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
          <Button size="small" type="primary" onClick={() => openConvert(record)}>Convert</Button>
        </Space>
      ),
    },
  ];

  const BudgetInfo = ({ productId, costCenterId, requestDate }) => {
    const [info, setInfo] = useState({ qty: '', used: '', remaining: '' });
    useEffect(() => {
      let cancelled = false;
      const load = async () => {
        if (!productId || !costCenterId || !requestDate) { setInfo({ qty: '', used: '', remaining: '' }); return; }
        try {
          const { data } = await api.get('/api/v1/budgets/lines/', { params: { cost_center: costCenterId, product: productId, date: requestDate.format('YYYY-MM-DD') } });
          const line = Array.isArray(data?.results) ? data.results[0] : Array.isArray(data) ? data[0] : null;
          if (!cancelled) {
            setInfo({
              qty: line?.approved_quantity ?? '',
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
    }, [productId, costCenterId, requestDate]);
    return (
      <>
        <Form.Item label="Budget Qty"><Input disabled value={info.qty} /></Form.Item>
        <Form.Item label="Used Qty"><Input disabled value={info.used} /></Form.Item>
        <Form.Item label="Remaining Qty"><Input disabled value={info.remaining} /></Form.Item>
      </>
    );
  };

  const LineRow = ({ name, restField, onRemove, form }) => {
    const productId = Form.useWatch([name, 'item_id'], form);
    const requestDate = Form.useWatch('request_date', form);
    const selectedItem = useMemo(() => (budgetItems || []).find(p => p.id === productId), [productId, budgetItems]);

    useEffect(() => {
      if (selectedItem) {
        const lines = form.getFieldValue('lines');
        if (lines && lines[name]) {
          lines[name].uom = selectedItem.uom;
          form.setFieldsValue({ lines });
        }
      }
    }, [selectedItem, name, form]);

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 120px 100px 240px 160px 160px 160px auto', columnGap: 8, alignItems: 'end', marginBottom: 8 }}>
        <Form.Item {...restField} name={[name, 'item_id']} label="Item" rules={[{ required: true, message: 'Select item' }]}>
          <Select
            showSearch
            filterOption={(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())}
            loading={budgetItemsLoading}
            placeholder="Select item"
            optionFilterProp="label"
            style={{ minWidth: 260 }}
            options={(budgetItems || []).map((p) => ({ value: p.id, label: `${p.code || ''} ${p.name}` }))}
          />
        </Form.Item>
        <Form.Item {...restField} name={[name, 'quantity']} label="Qty" rules={[{ required: true, message: 'Qty' }] }>
          <InputNumber min={0.001} step={1} style={{ width: 120 }} />
        </Form.Item>
        <Form.Item {...restField} name={[name, 'uom']} label="UoM">
          <Input placeholder="EA" style={{ width: 100 }} disabled />
        </Form.Item>
        <Form.Item {...restField} name={[name, 'notes']} label="Notes">
          <Input placeholder="Optional" style={{ width: 240 }} />
        </Form.Item>
        <BudgetInfo productId={productId} costCenterId={selectedCostCenter} requestDate={requestDate} />
        <Button
          aria-label="Remove line"
          type="text"
          danger
          shape="circle"
          icon={<CloseOutlined />}
          onClick={onRemove}
        />
      </div>
    );
  };

  const handleCreate = async (values) => {
    const payload = {
      req_no: values.req_no || undefined,
      request_date: values.request_date ? values.request_date.format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      needed_by: values.needed_by ? values.needed_by.format('YYYY-MM-DD') : null,
      purpose: values.purpose || '',
      status: 'SUBMITTED',
      lines: (values.lines || []).map((ln, idx) => ({
        line_no: idx + 1,
        item_id: ln.item_id,
        item_name: budgetItems.find((p) => String(p.id) === String(ln.item_id))?.name || '',
        quantity: Number(ln.quantity) || 0,
        uom: ln.uom || 'EA',
        notes: ln.notes || '',
      })),
    };

    try {
      setSubmitting(true);
      const { data } = await api.post('/api/v1/procurement/requisitions/', payload);
      message.success('Purchase requisition submitted');
      setOpen(false);
      formCreate.resetFields();
      setList((prev) => [data, ...prev]);
    } catch (_err) {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const existing = raw ? JSON.parse(raw) : [];
        const saved = [{ id: `local-${Date.now()}`, ...payload }, ...existing];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
        setList(saved);
        message.success('Saved locally (offline mode)');
        setOpen(false);
        formCreate.resetFields();
      } catch {
        message.error('Unable to save requisition');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <Title level={2}>Purchase Requisitions</Title>
      <Text type="secondary">Raise material requests for procurement and approval workflow.</Text>
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
            <Button onClick={() => {
              const rows = (Array.isArray(list) ? list : []).map((r) => ({
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
              a.download = 'purchase_requisitions_draft.csv';
              a.click();
              URL.revokeObjectURL(url);
            }}>Export CSV</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Make Requisition</Button>
          </Space>
        )}
      >
        <Table rowKey={(r) => r.id || r.req_no} loading={loading} dataSource={(Array.isArray(list) ? list : []).filter((r) => {
          let ok = true;
          if (Array.isArray(dateRange) && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
            const [start, end] = dateRange;
            const d = r.request_date ? dayjs(r.request_date) : null;
            ok = !!(d && d.isAfter(start.startOf('day')) && d.isBefore(end.endOf('day')));
          }
          return ok;
        })} columns={columns} pagination={{ pageSize: 10 }} />
      </Card>

      <Modal
        title="Create Purchase Requisition"
        open={open}
        width={1200}
        bodyStyle={{ overflowX: 'auto' }}
        onCancel={() => {
          setOpen(false);
          if (onCloseNew) onCloseNew();
        }}
        destroyOnClose
        footer={[
          <Button key="back" onClick={() => {
            setOpen(false);
            if (onCloseNew) onCloseNew();
          }}>
            Cancel
          </Button>,
          <Button key="submit" type="primary" loading={submitting} onClick={() => formCreate.submit()}>
            Submit
          </Button>,
        ]}
      >
        <Form layout="vertical" form={formCreate} onFinish={handleCreate} initialValues={{ request_date: dayjs(), lines: [{}, {}], _cc: selectedCostCenter }}>
          <Space size={16} style={{ display: 'flex', marginBottom: 8 }}>
            <Form.Item name="_cc" label="Cost Center" rules={[{ required: true }]}>
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="Select cost center"
                value={selectedCostCenter}
                onChange={(val) => { setSelectedCostCenter(val); try { localStorage.setItem('twist-default-cost-center', String(val)); } catch (_) {} }}
                options={ccOptions}
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
            <Form.Item label="Purpose/Notes" name="purpose" style={{ minWidth: 300 }}>
              <Input.TextArea rows={2} placeholder="Optional" />
            </Form.Item>
          </Space>

          <Form.List name="lines">
            {(fields, { add, remove }) => (
              <Card title="Items" size="small" extra={<Button onClick={() => add()}>Add Line</Button>}>
                {fields.map(({ key, name, ...restField }) => (
                  <LineRow key={key} name={name} restField={restField} onRemove={() => remove(name)} form={formCreate} />
                ))}
              </Card>
            )}
          </Form.List>
        </Form>
      </Modal>
      <Modal
        title={`Convert Draft ${convertTarget?.requisition_number || ''}`}
        open={convertOpen}
        onCancel={() => setConvertOpen(false)}
        onOk={async () => {
          try {
            const values = await formConvert.validateFields(['_cc', '_bl', '_keep']);
            setConverting(true);
            const { data } = await api.post(`/api/v1/procurement/requisitions/${convertTarget.id}/convert/`, {
              cost_center_id: values._cc,
              budget_line_id: values._bl,
              submit: true,
              keep_draft: !!values._keep,
            });
            message.success(`Converted to Purchase Requisition ${data?.requisition_number || ''}`);
            setConvertOpen(false);
            setConvertTarget(null);
            await loadRequisitions();
            // Navigate to PR list and auto-open the created PR
            const prKey = data?.requisition_number || data?.id;
            if (prKey) {
              navigate(`/procurement/requisitions?open=${encodeURIComponent(prKey)}`);
            }
          } catch (e) {
            if (e?.errorFields) return; // validation error
            message.error('Conversion failed');
          } finally {
            setConverting(false);
          }
        }}
        confirmLoading={converting}
      >
        <Form layout="vertical" form={formConvert}>
          <Form.Item label="Cost Center" name="_cc" rules={[{ required: true }]}
            extra="Choose the cost center under which this PR will be created."
          >
            <Select options={ccOptions} showSearch optionFilterProp="label" onChange={(val) => loadBudgetLines(val)} />
          </Form.Item>
          <Form.Item label="Budget Line" name="_bl" rules={[{ required: true }]}
            extra="Select a budget line appropriate for the items."
          >
            <Select options={blOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="_keep" valuePropName="checked">
            <Checkbox>Keep draft after conversion</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PurchaseRequisitions;
