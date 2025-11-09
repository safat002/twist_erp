import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, DatePicker, Form, Input, Modal, Select, Space, Spin, Switch, Table, Tag, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

import { createBudget, fetchBudgets, fetchCostCenters, openEntry, closeEntry } from '../../services/budget';
import { useCompany } from '../../contexts/CompanyContext';

const { Title } = Typography;

const NAME_STATUS_COLORS = { DRAFT: 'default', APPROVED: 'blue', REJECTED: 'red' };

const BudgetsList = () => {
  const navigate = useNavigate();
  const { currentCompany, companies, switchCompany } = useCompany();
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [period, setPeriod] = useState([dayjs().startOf('year'), dayjs().endOf('year')]);
  const [budgetModalOpen, setBudgetModalOpen] = useState(false);
  const [budgetForm] = Form.useForm();
  const [ccOptions, setCcOptions] = useState([]);
  const [ccLoading, setCcLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const params = {};
        const { data } = await fetchBudgets(params);
        setRows(data?.results || data || []);
      } catch (error) {
        console.error('Unable to load budgets', error);
        message.error(error?.response?.data?.detail || 'Unable to load budgets');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const dataSource = useMemo(() => {
    return rows
      .filter((row) => {
        if (statusFilter !== 'all' && String(row.name_status || '').toUpperCase() !== String(statusFilter).toUpperCase()) {
          return false;
        }
        if (search) {
          const term = search.toLowerCase();
          const haystack = (row.name || '').toLowerCase() + ' ' + (row.cost_center_name || row.cost_center || '').toLowerCase();
          if (!haystack.includes(term)) {
            return false;
          }
        }
        if (period && period[0] && period[1]) {
          const start = dayjs(row.period_start);
          if (start.isBefore(period[0]) || start.isAfter(period[1])) {
            return false;
          }
        }
        return true;
      })
      .map((row) => ({ ...row, key: row.id }));
  }, [rows, search, statusFilter, period]);

  const handleBudgetSave = async () => {
    try {
      const values = await budgetForm.validateFields();
      const [periodStart, periodEnd] = values.period || [];
      const [entryStart, entryEnd] = values.entry_window || [];
      const [reviewStart, reviewEnd] = values.review_window || [];
      const payload = {
        name: values.name,
        budget_type: values.budget_type,
        threshold_percent: values.threshold_percent ?? 90,
        period_start: periodStart ? periodStart.format('YYYY-MM-DD') : undefined,
        period_end: periodEnd ? periodEnd.format('YYYY-MM-DD') : undefined,
        entry_start_date: entryStart ? entryStart.format('YYYY-MM-DD') : undefined,
        entry_end_date: entryEnd ? entryEnd.format('YYYY-MM-DD') : undefined,
        entry_enabled: values.entry_enabled === undefined ? true : values.entry_enabled,
        company: values.company || currentCompany?.id,
        cost_center: values.cost_center || undefined,
        review_start_date: reviewStart ? reviewStart.format('YYYY-MM-DD') : undefined,
        review_end_date: reviewEnd ? reviewEnd.format('YYYY-MM-DD') : undefined,
        review_enabled: values.review_enabled === undefined ? !!(reviewStart && reviewEnd) : !!values.review_enabled,
      };
      // Ensure backend context matches selected company if different
      if (values.company && String(values.company) !== String(currentCompany?.id)) {
        try {
          await switchCompany(values.company);
        } catch (_) {
          // Proceed even if switch fails; backend may accept company in payload
        }
      }
      await createBudget(payload);
      message.success('Budget created');
      setBudgetModalOpen(false);
      budgetForm.resetFields();
      // Reload list
      setLoading(true);
      try {
        const { data } = await fetchBudgets({});
        setRows(data?.results || data || []);
      } finally {
        setLoading(false);
      }
    } catch (error) {
      if (error?.errorFields) return;
      const data = error?.response?.data;
      let msg = data?.detail;
      if (!msg && data && typeof data === 'object') {
        try {
          const first = Object.values(data)[0];
          if (Array.isArray(first) && first.length) msg = first[0];
        } catch (_) {}
      }
      message.error(msg || 'Failed to create budget');
    }
  };

  const columns = [
    {
      title: 'Budget',
      dataIndex: 'name',
      key: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Button
            type="link"
            style={{ padding: 0, height: 'auto' }}
            onClick={() => navigate(`/budgets?edit=${record.id}`)}
          >
            {value || 'Untitled Budget'}
          </Button>
          <span style={{ color: '#8c8c8c', fontSize: 12 }}>{record.cost_center_name || record.cost_center}</span>
        </Space>
      ),
    },
    {
      title: 'Entry Window',
      key: 'entry_window',
      render: (_, record) => {
        const isEnabled = !!record.entry_enabled;
        const label = isEnabled ? 'Close Entry' : 'Open Entry';
        // Disable toggle after end of entry window or budget period
        const today = dayjs().startOf('day');
        const entryEnd = record.entry_end_date ? dayjs(record.entry_end_date) : null;
        const periodEnd = record.period_end ? dayjs(record.period_end) : null;
        const pastEnd = (entryEnd && today.isAfter(entryEnd)) || (periodEnd && today.isAfter(periodEnd));
        return (
          <Button
            size="small"
            disabled={pastEnd}
            onClick={async () => {
              if (pastEnd) return;
              try {
                if (isEnabled) {
                  await closeEntry(record.id);
                  message.success('Entry window closed');
                } else {
                  await openEntry(record.id);
                  message.success('Entry window opened');
                }
                // Reload budgets
                setLoading(true);
                try {
                  const { data } = await fetchBudgets({});
                  setRows(data?.results || data || []);
                } finally {
                  setLoading(false);
                }
              } catch (e) {
                message.error(e?.response?.data?.detail || 'Failed to toggle entry window');
              }
            }}
          >
            {label}
          </Button>
        );
      },
    },
    {
      title: 'Type',
      dataIndex: 'budget_type',
      key: 'budget_type',
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: 'Period',
      dataIndex: 'period_start',
      key: 'period',
      render: (_, record) => record.period_start + ' to ' + record.period_end,
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (value) => Number(value || 0).toLocaleString(),
    },
    {
      title: 'Consumed',
      dataIndex: 'consumed',
      key: 'consumed',
      render: (value, record) => {
        const consumed = Number(value || 0);
        const limit = Number(record.amount || 0);
        const percent = limit > 0 ? Math.round((consumed / limit) * 100) : 0;
        return consumed.toLocaleString() + ' (' + percent + '%)';
      },
    },
    {
      title: 'Name Status',
      key: 'name_status',
      render: (_, record) => {
        const ns = String(record.name_status || ((String(record.status || '').toLowerCase() === 'pending_name_approval') ? 'DRAFT' : 'APPROVED'));
        const key = ns.toUpperCase();
        const color = NAME_STATUS_COLORS[key] || 'default';
        return <Tag color={color}>{key}</Tag>;
      },
    },
    {
      title: 'Windows',
      dataIndex: 'status2',
      key: 'status2',
      render: (value) => {
        if (value && typeof value === 'object') {
          const entry = (value.entry?.state || '').replace('_', ' ');
          const review = (value.review?.state || '').replace('_', ' ');
          const period = (value.period?.state || '').replace('_', ' ');
          const colorFor = (s) => (s === 'open' ? 'green' : (s === 'closed' ? 'red' : 'default'));
          return (
            <Space size={4} wrap>
              <Tag color={colorFor(entry)}>Entry: {entry || '-'}</Tag>
              <Tag color={colorFor(review)}>Review: {review || '-'}</Tag>
              <Tag color={colorFor(period)}>Period: {period || '-'}</Tag>
            </Space>
          );
        }
        return <span>{value || ''}</span>;
      },
    },
  ];

  return (
    <Spin spinning={loading} tip="Loading budgets">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Title level={3} style={{ marginBottom: 0 }}>Budget Registry</Title>
            <span style={{ display: 'none' }}>
              {currentCompany ? currentCompany.name + ' · ' + currentCompany.code : 'Select a company to view budgets'}
            </span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                budgetForm.resetFields();
                budgetForm.setFieldsValue({
                  budget_type: 'operational',
                  threshold_percent: 90,
                  period: [dayjs().startOf('month'), dayjs().endOf('month')],
                  entry_window: [dayjs().startOf('month'), dayjs().endOf('month')],
                  review_window: undefined,
                  company: currentCompany?.id,
                });
                // Load CC for selected company
                const cId = currentCompany?.id;
                if (cId) {
                  setCcLoading(true);
                  fetchCostCenters({ company: cId, limit: 1000 })
                    .then((res) => {
                      const rows = res.data?.results || res.data || [];
                      setCcOptions(rows.map((cc) => ({ value: cc.id, label: `${cc.code} - ${cc.name || 'Unnamed'}` })));
                    })
                    .catch(() => setCcOptions([]))
                    .finally(() => setCcLoading(false));
                } else {
                  setCcOptions([]);
                }
                setBudgetModalOpen(true);
              }}
            >
              New Budget
            </Button>
          </div>
          <Space wrap>
            <Input.Search
              placeholder="Search budget or cost center"
              allowClear
              onSearch={setSearch}
              style={{ width: 240 }}
            />
            <Select
              value={statusFilter}
              style={{ width: 160 }}
              onChange={setStatusFilter}
              options={[
                { value: 'all', label: 'All name statuses' },
                { value: 'DRAFT', label: 'Draft' },
                { value: 'APPROVED', label: 'Approved' },
                { value: 'REJECTED', label: 'Rejected' },
              ]}
            />
            <DatePicker.RangePicker
              value={period}
              onChange={(value) => setPeriod(value)}
              allowEmpty={[false, false]}
            />
          </Space>
          <Table columns={columns} dataSource={dataSource} pagination={{ pageSize: 12 }} />

          <Modal
            title="New Budget"
            open={budgetModalOpen}
            onCancel={() => {
              setBudgetModalOpen(false);
              budgetForm.resetFields();
            }}
            onOk={handleBudgetSave}
            okText="Create"
            destroyOnClose
          >
            <Form
              layout="vertical"
              form={budgetForm}
              onValuesChange={(changed, all) => {
                if (Object.prototype.hasOwnProperty.call(changed, 'company')) {
                  const companyId = changed.company;
                  if (companyId) {
                    setCcLoading(true);
                    fetchCostCenters({ company: companyId, limit: 1000 })
                      .then((res) => {
                        const rows = res.data?.results || res.data || [];
                        setCcOptions(rows.map((cc) => ({ value: cc.id, label: `${cc.code} - ${cc.name || 'Unnamed'}` })));
                      })
                      .catch(() => setCcOptions([]))
                      .finally(() => setCcLoading(false));
                  } else {
                    setCcOptions([]);
                  }
                }
              }}
            >
              <Form.Item label="Company" name="company" rules={[{ required: true, message: 'Select company' }]}>
                <Select
                  placeholder="Select company"
                  options={(companies || []).map((c) => ({ value: c.id, label: `${c.name} (${c.code})` }))}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
              <Form.Item label="Cost Center (optional)" name="cost_center">
                <Select
                  placeholder={ccLoading ? 'Loading cost centers...' : 'Select a cost center (optional)'}
                  options={ccOptions}
                  loading={ccLoading}
                  allowClear
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
              <Form.Item label="Name" name="name" rules={[{ required: true }]}>
                <Input placeholder="FY25 Operations" />
              </Form.Item>
              <Form.Item label="Budget Type" name="budget_type" initialValue="operational">
                <Select
                  options={[
                    { value: 'operational', label: 'Operational / Production' },
                    { value: 'opex', label: 'Department OPEX' },
                    { value: 'capex', label: 'Capital Expenditure' },
                    { value: 'revenue', label: 'Revenue Target' },
                  ]}
                />
              </Form.Item>
              <Form.Item label="Period" name="period" rules={[{ required: true, message: 'Select a budget period' }]}>
                <DatePicker.RangePicker allowClear={false} format="YYYY-MM-DD" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Entry Window" name="entry_window" rules={[{ required: true, message: 'Select entry start/end dates' }]}>
                <DatePicker.RangePicker allowClear={false} format="YYYY-MM-DD" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Review Window" name="review_window">
                <DatePicker.RangePicker allowClear format="YYYY-MM-DD" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Review Enabled" name="review_enabled" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="Entry Enabled" name="entry_enabled" valuePropName="checked" initialValue={true}>
                <Switch />
              </Form.Item>
              <Form.Item label="Threshold %" name="threshold_percent" initialValue={90}>
                <Input type="number" min={50} max={100} />
              </Form.Item>
            </Form>
          </Modal>
        </Space>
      </Card>
    </Spin>
  );
};

export default BudgetsList;
