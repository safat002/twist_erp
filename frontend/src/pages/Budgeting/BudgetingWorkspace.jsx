import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  AlertOutlined,
  CheckCircleOutlined,
  FundOutlined,
  PartitionOutlined,
  PlusOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  approveBudget,
  approveOverride,
  closeBudget,
  createBudget,
  createBudgetLine,
  createOverrideRequest,
  createCostCenter,
  checkBudgetAvailability,
  fetchBudgetLines,
  fetchBudgetWorkspaceSummary,
  fetchBudgets,
  fetchCostCenters,
  fetchOverrides,
  lockBudget,
  recordBudgetUsage,
  rejectOverride,
  recalculateBudget,
  submitBudget,
  updateBudget,
  updateBudgetLine,
  updateCostCenter,
} from '../../services/budget';
import { searchUsers } from '../../services/users';
import { useCompany } from '../../contexts/CompanyContext';

const { Title, Text } = Typography;

const STATUS_COLORS = {
  DRAFT: 'default',
  PROPOSED: 'geekblue',
  UNDER_REVIEW: 'purple',
  ACTIVE: 'green',
  LOCKED: 'gold',
  CLOSED: 'magenta',
  ARCHIVED: 'red',
};

const PROCUREMENT_OPTIONS = [
  { value: 'stock_item', label: 'Stock Item' },
  { value: 'service_item', label: 'Service / Expense' },
  { value: 'capex_item', label: 'Capex Item' },
];

const formatCurrency = (value) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value ?? '0';
  }
  return numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const BudgetingWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [costCenters, setCostCenters] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [overrides, setOverrides] = useState([]);
  const [budgetLines, setBudgetLines] = useState({});
  const [activeBudget, setActiveBudget] = useState(null);

  const [costCenterModalOpen, setCostCenterModalOpen] = useState(false);
  const [budgetModalOpen, setBudgetModalOpen] = useState(false);
  const [lineModalOpen, setLineModalOpen] = useState(false);
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [usageModalOpen, setUsageModalOpen] = useState(false);

  const [costCenterForm] = Form.useForm();
  const [budgetForm] = Form.useForm();
  const [lineForm] = Form.useForm();
  const [overrideForm] = Form.useForm();
  const [usageForm] = Form.useForm();

  const [userOptions, setUserOptions] = useState([]);
  const [userLookupLoading, setUserLookupLoading] = useState(false);
  const userSearchTimeout = useRef();

  const [overrideAvailability, setOverrideAvailability] = useState(null);
  const [overrideAvailabilityError, setOverrideAvailabilityError] = useState(null);
  const [checkingOverride, setCheckingOverride] = useState(false);
  const [lineAvailability, setLineAvailability] = useState(null);
  const [lineAvailabilityError, setLineAvailabilityError] = useState(null);
  const [checkingLine, setCheckingLine] = useState(false);

  const overrideCostCenter = Form.useWatch('cost_center', overrideForm);
  const overrideAmount = Form.useWatch('requested_amount', overrideForm);
  const overrideLine = Form.useWatch('budget_line', overrideForm);
  const lineValueLimit = Form.useWatch('value_limit', lineForm);
  const lineProcurementClass = Form.useWatch('procurement_class', lineForm);

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryRes, costCenterRes, budgetsRes, overridesRes] = await Promise.all([
        fetchBudgetWorkspaceSummary(),
        fetchCostCenters(),
        fetchBudgets(),
        fetchOverrides({ limit: 50 }),
      ]);
      setSummary(summaryRes.data || {});
      setCostCenters(costCenterRes.data?.results || costCenterRes.data || []);
      setBudgets(budgetsRes.data?.results || budgetsRes.data || []);
      setOverrides(overridesRes.data?.results || overridesRes.data || []);
    } catch (error) {
      console.error('Failed to load budgeting workspace', error);
      message.error(error?.response?.data?.detail || 'Unable to load budgeting workspace');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  const lineLookup = useMemo(() => {
    const map = {};
    Object.values(budgetLines || {}).forEach((collection) => {
      (collection || []).forEach((line) => {
        map[line.id] = line;
      });
    });
    return map;
  }, [budgetLines]);

  const loadUsers = useCallback(
    async (search = '') => {
      setUserLookupLoading(true);
      try {
        const { data } = await searchUsers({ search, limit: 20 });
        const rows = data?.results || data || [];
        const mapped = rows.map((user) => ({
          value: user.id,
          label: user.display_name || user.full_name || user.username,
        }));
        setUserOptions((prev) => {
          const existing = new Map((prev || []).map((option) => [option.value, option]));
          mapped.forEach((option) => {
            existing.set(option.value, option);
          });
          return Array.from(existing.values());
        });
      } catch (error) {
        console.error('Failed to load users', error);
        message.error(error?.response?.data?.detail || 'Unable to load users');
      } finally {
        setUserLookupLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    loadUsers();
    return () => {
      if (userSearchTimeout.current) {
        clearTimeout(userSearchTimeout.current);
      }
    };
  }, [loadUsers]);

  const handleUserSearch = useCallback(
    (query) => {
      if (userSearchTimeout.current) {
        clearTimeout(userSearchTimeout.current);
      }
      userSearchTimeout.current = setTimeout(() => {
        loadUsers(query);
      }, 300);
    },
    [loadUsers],
  );

  useEffect(() => {
    const amountValue = parseFloat(overrideAmount);
    if (!overrideCostCenter || Number.isNaN(amountValue) || amountValue <= 0) {
      setOverrideAvailability(null);
      setOverrideAvailabilityError(null);
      setCheckingOverride(false);
      return;
    }
    let cancelled = false;
    setCheckingOverride(true);
    setOverrideAvailabilityError(null);
    const timer = setTimeout(async () => {
      try {
        const payload = { cost_center: overrideCostCenter, amount: amountValue };
        const selectedLine = overrideLine ? lineLookup[overrideLine] : null;
        if (selectedLine?.procurement_class) {
          payload.procurement_class = selectedLine.procurement_class;
        }
        const { data } = await checkBudgetAvailability(payload);
        if (!cancelled) {
          setOverrideAvailability(data);
          setOverrideAvailabilityError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setOverrideAvailability(null);
          setOverrideAvailabilityError(error?.response?.data?.detail || 'Unable to check availability');
        }
      } finally {
        if (!cancelled) {
          setCheckingOverride(false);
        }
      }
    }, 350);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [overrideCostCenter, overrideAmount, overrideLine, lineLookup]);

  useEffect(() => {
    const amountValue = parseFloat(lineValueLimit);
    if (!activeBudget?.cost_center || Number.isNaN(amountValue) || amountValue <= 0) {
      setLineAvailability(null);
      setLineAvailabilityError(null);
      setCheckingLine(false);
      return;
    }
    let cancelled = false;
    setCheckingLine(true);
    setLineAvailabilityError(null);
    const timer = setTimeout(async () => {
      try {
        const payload = {
          cost_center: activeBudget.cost_center,
          amount: amountValue,
        };
        if (lineProcurementClass) {
          payload.procurement_class = lineProcurementClass;
        }
        const { data } = await checkBudgetAvailability(payload);
        if (!cancelled) {
          setLineAvailability(data);
          setLineAvailabilityError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setLineAvailability(null);
          setLineAvailabilityError(error?.response?.data?.detail || 'Unable to check availability');
        }
      } finally {
        if (!cancelled) {
          setCheckingLine(false);
        }
      }
    }, 350);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [activeBudget, lineProcurementClass, lineValueLimit]);

  const ensureBudgetLines = useCallback(async (budgetId) => {
    if (budgetLines[budgetId]) {
      return;
    }
    try {
      const { data } = await fetchBudgetLines({ budget: budgetId, page_size: 500 });
      const rows = data?.results || data || [];
      setBudgetLines((prev) => ({ ...prev, [budgetId]: rows }));
    } catch (error) {
      console.error('Unable to load budget lines', error);
      message.error('Unable to load budget lines');
    }
  }, [budgetLines]);

  const handleCostCenterSave = async () => {
    try {
      const values = await costCenterForm.validateFields();
      if (values.id) {
        await updateCostCenter(values.id, { ...values, id: undefined });
      } else {
        await createCostCenter(values);
      }
      message.success('Cost center saved');
      setCostCenterModalOpen(false);
      costCenterForm.resetFields();
      loadWorkspace();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error?.response?.data?.detail || 'Failed to save cost center');
    }
  };

const handleBudgetSave = async () => {
  try {
    const values = await budgetForm.validateFields();
    const [periodStart, periodEnd] = values.period || [];
    const payload = {
      ...values,
      period_start: periodStart ? periodStart.format('YYYY-MM-DD') : undefined,
      period_end: periodEnd ? periodEnd.format('YYYY-MM-DD') : undefined,
    };
    delete payload.period;
    if (values.id) {
      await updateBudget(values.id, payload);
    } else {
      await createBudget(payload);
    }
    message.success('Budget saved');
    setBudgetModalOpen(false);
    budgetForm.resetFields();
    loadWorkspace();
  } catch (error) {
    if (error?.errorFields) {
      return;
    }
    message.error(error?.response?.data?.detail || 'Failed to save budget');
  }
};

  const handleBudgetLineSave = async () => {
    try {
      const values = await lineForm.validateFields();
      if (values.id) {
        await updateBudgetLine(values.id, values);
      } else {
        await createBudgetLine(values);
      }
      message.success('Budget line saved');
      setLineModalOpen(false);
      lineForm.resetFields();
      setLineAvailability(null);
      setLineAvailabilityError(null);
      if (activeBudget) {
        setBudgetLines((prev) => ({ ...prev, [activeBudget.id]: undefined }));
        ensureBudgetLines(activeBudget.id);
      }
      loadWorkspace();
  } catch (error) {
    if (error?.errorFields) {
      return;
    }
    const detail = error?.response?.data?.detail || 'Failed to save budget line';
    message.error(detail);
    setLineAvailabilityError(detail);
  }
};

const handleOverrideSave = async () => {
  try {
      const values = await overrideForm.validateFields();
      await createOverrideRequest(values);
      message.success('Override request submitted');
      setOverrideModalOpen(false);
    overrideForm.resetFields();
    setOverrideAvailability(null);
    setOverrideAvailabilityError(null);
    loadWorkspace();
  } catch (error) {
    if (error?.errorFields) {
      return;
    }
    const detail = error?.response?.data?.detail || 'Failed to submit override';
    message.error(detail);
    setOverrideAvailabilityError(detail);
  }
};

  const handleUsageSave = async () => {
    try {
      const values = await usageForm.validateFields();
      await recordBudgetUsage(values);
      message.success('Budget usage recorded');
      setUsageModalOpen(false);
      usageForm.resetFields();
      if (activeBudget) {
        setBudgetLines((prev) => ({ ...prev, [activeBudget.id]: undefined }));
        ensureBudgetLines(activeBudget.id);
      }
      loadWorkspace();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error?.response?.data?.detail || 'Failed to record budget usage');
    }
  };

  const budgetColumns = useMemo(() => [
    {
      title: 'Budget',
      dataIndex: 'name',
      key: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value || 'Untitled Budget'}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.cost_center_name || record.cost_center}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Period',
      dataIndex: 'period_start',
      key: 'period',
      render: (_, record) => (
        <Text>
          {record.period_start} to {record.period_end}
        </Text>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'budget_type',
      key: 'budget_type',
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: 'Consumption',
      key: 'consumption',
      render: (_, record) => {
        const consumed = Number(record.consumed || 0);
        const limit = Number(record.amount || 0);
        const percent = limit > 0 ? Number(((consumed / limit) * 100).toFixed(1)) : 0;
        const status = percent >= 95 ? 'exception' : 'active';
        return (
          <div style={{ minWidth: 180 }}>
            <Progress percent={percent} size="small" status={status} />
            <Text type="secondary">
              {consumed.toLocaleString()} / {limit.toLocaleString()} {currentCompany?.currency_code || ''}
            </Text>
          </div>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => <Tag color={STATUS_COLORS[value] || 'default'}>{value}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            onClick={() => {
              const start = record.period_start ? dayjs(record.period_start) : dayjs();
              const end = record.period_end ? dayjs(record.period_end) : start;
              setActiveBudget(record);
              budgetForm.resetFields();
              budgetForm.setFieldsValue({
                id: record.id,
                name: record.name,
                cost_center: record.cost_center,
                budget_type: record.budget_type,
                amount: record.amount,
                threshold_percent: record.threshold_percent,
                period: [start, end],
              });
              setBudgetModalOpen(true);
            }}
          >
            Edit
          </Button>
          <Button
            type="link"
            onClick={() => {
              setActiveBudget(record);
              ensureBudgetLines(record.id);
              lineForm.resetFields();
              lineForm.setFieldsValue({ budget: record.id, procurement_class: 'stock_item', tolerance_percent: 5 });
              setLineModalOpen(true);
            }}
          >
            Add line
          </Button>
          <Button
            type="link"
            onClick={() => {
              setActiveBudget(record);
              ensureBudgetLines(record.id);
              usageForm.resetFields();
              usageForm.setFieldsValue({
                budget_line: undefined,
                usage_type: 'stock_issue',
                usage_date: dayjs().format('YYYY-MM-DD'),
              });
              setUsageModalOpen(true);
            }}
          >
            Usage
          </Button>
          {record.status === 'DRAFT' && (
            <Button type="link" onClick={() => submitBudget(record.id)}>Submit</Button>
          )}
          {record.status === 'PROPOSED' && (
            <Button type="link" onClick={() => approveBudget(record.id)}>Approve</Button>
          )}
          {record.status === 'ACTIVE' && (
            <Button type="link" onClick={() => lockBudget(record.id)}>Lock</Button>
          )}
          {record.status === 'LOCKED' && (
            <Button type="link" onClick={() => closeBudget(record.id)}>Close</Button>
          )}
          <Button type="link" onClick={() => recalculateBudget(record.id)}>Recalc</Button>
        </Space>
      ),
    },
  ], [budgetForm, currentCompany, ensureBudgetLines, lineForm]);

  const costCenterColumns = [
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Type',
      dataIndex: 'cost_center_type',
      key: 'cost_center_type',
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: 'Owner',
      dataIndex: 'owner_display',
      key: 'owner_display',
      render: (value) => value || <Text type="secondary">Unassigned</Text>,
    },
    {
      title: 'Active Budgets',
      dataIndex: 'active_budget_count',
      key: 'active_budget_count',
      render: (value) => <Badge count={value || 0} />, 
    },
  ];

  const overrideColumns = [
    {
      title: 'Reference',
      dataIndex: 'reference_id',
      key: 'reference_id',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value || 'Override #' + record.id}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.cost_center_name}</Text>
        </Space>
      ),
    },
    {
      title: 'Amount',
      dataIndex: 'requested_amount',
      key: 'requested_amount',
      render: (value) => <Text>{Number(value || 0).toLocaleString()}</Text>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => <Tag color={value === 'PENDING' ? 'orange' : value === 'APPROVED' ? 'green' : 'red'}>{value}</Tag>,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        record.status === 'PENDING' ? (
          <Space>
            <Button type="link" onClick={() => approveOverride(record.id)}>Approve</Button>
            <Button type="link" danger onClick={() => rejectOverride(record.id)}>Reject</Button>
          </Space>
        ) : (
          <Text type="secondary">Processed</Text>
        )
      ),
    },
  ];

  const pendingOverrideCount = overrides.filter((item) => item.status === 'PENDING').length;

  return (
    <Spin spinning={loading} tip="Loading budgeting workspace">
      <div>
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={2} style={{ marginBottom: 0 }}>Budget & Cost Control</Title>
            <Text type="secondary">
              {currentCompany ? currentCompany.name + ' (' + currentCompany.code + ')' : 'Select a company to begin'}
            </Text>
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setActiveBudget(null);
                  budgetForm.resetFields();
                  budgetForm.setFieldsValue({
                    budget_type: 'operational',
                    threshold_percent: 90,
                    period: [dayjs().startOf('month'), dayjs().endOf('month')],
                  });
                  setBudgetModalOpen(true);
                }}
              >
                New Budget
              </Button>
              <Button icon={<UserSwitchOutlined />} onClick={() => setCostCenterModalOpen(true)}>New Cost Center</Button>
              <Button icon={<AlertOutlined />} onClick={() => setOverrideModalOpen(true)}>Override</Button>
            </Space>
          </Col>
        </Row>

        <Tabs defaultActiveKey="overview">
          <Tabs.TabPane tab="Overview" key="overview">
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card>
                  <Statistic title="Cost Centers" value={summary?.cost_center_count || 0} prefix={<PartitionOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="Budgets" value={summary?.budget_count || 0} prefix={<FundOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="Pending Overrides" value={pendingOverrideCount} prefix={<AlertOutlined />} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="Snapshots" value={summary?.snapshots || 0} prefix={<CheckCircleOutlined />} />
                </Card>
              </Col>
            </Row>
            {pendingOverrideCount === 0 ? (
              <Alert type="success" showIcon message="No pending override requests." />
            ) : (
              <Card title="Pending Overrides">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {overrides.filter((item) => item.status === 'PENDING').map((item) => (
                    <Card key={item.id} size="small">
                      <Space direction="vertical" size={0} style={{ width: '100%' }}>
                        <Text strong>{item.reference_id || 'Override #' + item.id}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{item.cost_center_name}</Text>
                        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                          <Text>{Number(item.requested_amount || 0).toLocaleString()}</Text>
                          <Space>
                            <Button type="link" size="small" onClick={() => approveOverride(item.id)}>Approve</Button>
                            <Button type="link" size="small" danger onClick={() => rejectOverride(item.id)}>Reject</Button>
                          </Space>
                        </Space>
                      </Space>
                    </Card>
                  ))}
                </Space>
              </Card>
            )}
          </Tabs.TabPane>

          <Tabs.TabPane tab="Budgets" key="budgets">
            <Table rowKey="id" dataSource={budgets} columns={budgetColumns} pagination={{ pageSize: 10 }} />
            {activeBudget ? (
              <Card title={'Lines · ' + (activeBudget.name || activeBudget.id)} style={{ marginTop: 16 }}>
                <Table
                  rowKey="id"
                  dataSource={budgetLines[activeBudget.id] || []}
                  pagination={false}
                  columns={[
                    { title: 'Item', dataIndex: 'item_name', key: 'item_name' },
                    { title: 'Class', dataIndex: 'procurement_class', key: 'procurement_class', render: (value) => <Tag>{value}</Tag> },
                    {
                      title: 'Limit',
                      key: 'limit',
                      render: (_, record) => (
                        Number(record.value_limit || 0).toLocaleString() + ' (' + Number(record.qty_limit || 0) + ' units)'
                      ),
                    },
                    {
                      title: 'Consumed',
                      key: 'consumed',
                      render: (_, record) => (
                        <Space direction="vertical" size={0}>
                          <Text>{Number(record.consumed_value || 0).toLocaleString()}</Text>
                          <Progress
                            percent={record.value_limit > 0 ? Number(((record.consumed_value / record.value_limit) * 100).toFixed(1)) : 0}
                            size="small"
                            status={record.value_limit > 0 && record.consumed_value / record.value_limit >= 0.95 ? 'exception' : 'active'}
                          />
                        </Space>
                      ),
                    },
                  ]}
                />
              </Card>
            ) : (
              <Alert type="info" showIcon message="Select a budget row to review its lines." style={{ marginTop: 16 }} />
            )}
          </Tabs.TabPane>

          <Tabs.TabPane tab="Cost Centers" key="cost-centers">
            <Table rowKey="id" dataSource={costCenters} columns={costCenterColumns} pagination={{ pageSize: 10 }} />
          </Tabs.TabPane>

          <Tabs.TabPane tab="Overrides" key="overrides">
            <Table rowKey="id" dataSource={overrides} columns={overrideColumns} pagination={{ pageSize: 10 }} />
          </Tabs.TabPane>
        </Tabs>

        <Modal
          title="Cost Center"
          open={costCenterModalOpen}
          onCancel={() => {
            setCostCenterModalOpen(false);
            costCenterForm.resetFields();
          }}
          onOk={handleCostCenterSave}
          okText="Save"
          destroyOnClose
        >
          <Form layout="vertical" form={costCenterForm}>
            <Form.Item name="id" hidden><Input type="hidden" /></Form.Item>
            <Form.Item label="Code" name="code" rules={[{ required: true }]}>
              <Input placeholder="MKT" autoComplete="off" />
            </Form.Item>
            <Form.Item label="Name" name="name" rules={[{ required: true }]}>
              <Input placeholder="Marketing" autoComplete="off" />
            </Form.Item>
            <Form.Item label="Type" name="cost_center_type" initialValue="department">
              <Select
                options={[
                  { value: 'department', label: 'Department' },
                  { value: 'branch', label: 'Branch' },
                  { value: 'program', label: 'Program / Grant' },
                  { value: 'project', label: 'Project' },
                  { value: 'production_line', label: 'Production Line' },
                ]}
              />
            </Form.Item>
            <Form.Item label="Owner" name="owner">
              <Select
                allowClear
                showSearch
                placeholder="Assign owner (optional)"
                filterOption={false}
                onSearch={handleUserSearch}
                notFoundContent={userLookupLoading ? <Spin size="small" /> : null}
                options={userOptions}
              />
            </Form.Item>
            <Form.Item label="Backup Owner" name="deputy_owner">
              <Select
                allowClear
                showSearch
                placeholder="Assign backup owner (optional)"
                filterOption={false}
                onSearch={handleUserSearch}
                notFoundContent={userLookupLoading ? <Spin size="small" /> : null}
                options={userOptions}
              />
            </Form.Item>
            <Form.Item label="Default Currency" name="default_currency" initialValue={currentCompany?.currency_code || 'USD'}>
              <Input maxLength={3} />
            </Form.Item>
            <Form.Item label="Tags" name="tags">
              <Select mode="tags" placeholder="Add tags" />
            </Form.Item>
            <Form.Item label="Description" name="description">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Budget"
          open={budgetModalOpen}
          onCancel={() => {
            setBudgetModalOpen(false);
            budgetForm.resetFields();
            setActiveBudget(null);
          }}
          onOk={handleBudgetSave}
          okText="Save"
          destroyOnClose
        >
          <Form
            layout="vertical"
            form={budgetForm}
            initialValues={{
              budget_type: 'operational',
              threshold_percent: 90,
              period: [dayjs().startOf('month'), dayjs().endOf('month')],
            }}
          >
            <Form.Item name="id" hidden><Input type="hidden" /></Form.Item>
            <Form.Item label="Name" name="name" rules={[{ required: true }]}>
              <Input placeholder="FY25 Operations" />
            </Form.Item>
            <Form.Item label="Cost Center" name="cost_center" rules={[{ required: true }]}>
              <Select
                placeholder="Select cost center"
                options={costCenters.map((cc) => ({
                  value: cc.id,
                  label: `${cc.code} - ${cc.name || 'Unnamed'}`,
                }))}
              />
            </Form.Item>
            <Form.Item label="Budget Type" name="budget_type">
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
            <Form.Item label="Threshold %" name="threshold_percent">
              <Input type="number" min={50} max={100} />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Budget Line"
          open={lineModalOpen}
          onCancel={() => {
            setLineModalOpen(false);
            lineForm.resetFields();
            setLineAvailability(null);
            setLineAvailabilityError(null);
          }}
          onOk={handleBudgetLineSave}
          okText="Save"
          destroyOnClose
        >
          <Form layout="vertical" form={lineForm} initialValues={{ tolerance_percent: 5, procurement_class: 'stock_item' }}>
            <Form.Item name="id" hidden><Input type="hidden" /></Form.Item>
            <Form.Item name="budget" hidden initialValue={activeBudget?.id}><Input type="hidden" /></Form.Item>
            <Form.Item label="Procurement Class" name="procurement_class" rules={[{ required: true }]}>
              <Select options={PROCUREMENT_OPTIONS} />
            </Form.Item>
            <Form.Item label="Item Name" name="item_name" rules={[{ required: true }]}>
              <Input placeholder="Describe the item or service" />
            </Form.Item>
            <Form.Item label="Category" name="category">
              <Input placeholder="Optional category" />
            </Form.Item>
            <Form.Item label="Quantity Limit" name="qty_limit">
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item label="Value Limit" name="value_limit" rules={[{ required: true }]}>
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item noStyle>
              <div style={{ marginBottom: 16 }}>
                {checkingLine && <Alert type="info" showIcon message="Checking availability..." />}
                {!checkingLine && lineAvailability && (
                  <Alert
                    type={lineAvailability.available ? 'success' : 'warning'}
                    showIcon
                    message={lineAvailability.available ? 'Within available budget' : 'Budget exceeded'}
                    description={`Available: ${formatCurrency(lineAvailability.available_amount)} | Requested: ${formatCurrency(lineAvailability.requested)}`}
                  />
                )}
                {!checkingLine && !lineAvailability && lineAvailabilityError && (
                  <Alert type="error" showIcon message={lineAvailabilityError} />
                )}
              </div>
            </Form.Item>
            <Form.Item label="Standard Price" name="standard_price">
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item label="Tolerance %" name="tolerance_percent">
              <Input type="number" min={0} max={100} />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Override Request"
          open={overrideModalOpen}
          onCancel={() => {
            setOverrideModalOpen(false);
            overrideForm.resetFields();
            setOverrideAvailability(null);
            setOverrideAvailabilityError(null);
          }}
          onOk={handleOverrideSave}
          okText="Submit"
          destroyOnClose
        >
          <Form layout="vertical" form={overrideForm}>
            <Form.Item label="Cost Center" name="cost_center" rules={[{ required: true }]}>
              <Select
                options={costCenters.map((cc) => ({
                  value: cc.id,
                  label: `${cc.code} - ${cc.name || 'Unnamed'}`,
                }))}
              />
            </Form.Item>
            <Form.Item label="Budget Line" name="budget_line">
              <Select
                allowClear
                placeholder="Optional – link to a specific budget line"
                options={(activeBudget ? (budgetLines[activeBudget.id] || []) : []).map((line) => {
                  const remaining =
                    line.remaining_value ??
                    Number(line.value_limit || 0) - Number(line.consumed_value || 0);
                  return {
                    value: line.id,
                    label: `${line.item_name} (remaining ${formatCurrency(remaining)})`,
                  };
                })}
              />
            </Form.Item>
            <Form.Item label="Requested Amount" name="requested_amount" rules={[{ required: true }]}>
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item noStyle>
              <div style={{ marginBottom: 16 }}>
                {checkingOverride && <Alert type="info" showIcon message="Checking availability..." />}
                {!checkingOverride && overrideAvailability && (
                  <Alert
                    type={overrideAvailability.available ? 'success' : 'warning'}
                    showIcon
                    message={overrideAvailability.available ? 'Budget available' : 'Budget limit breached'}
                    description={`Available: ${formatCurrency(overrideAvailability.available_amount)} | Requested: ${formatCurrency(overrideAvailability.requested)}`}
                  />
                )}
                {!checkingOverride && !overrideAvailability && overrideAvailabilityError && (
                  <Alert type="error" showIcon message={overrideAvailabilityError} />
                )}
              </div>
            </Form.Item>
            <Form.Item label="Requested Quantity" name="requested_quantity">
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item label="Reason" name="reason" rules={[{ required: true }]}>
              <Input.TextArea rows={4} />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Record Usage"
          open={usageModalOpen}
          onCancel={() => {
            setUsageModalOpen(false);
            usageForm.resetFields();
          }}
          onOk={handleUsageSave}
          okText="Record"
          destroyOnClose
        >
          <Form layout="vertical" form={usageForm} initialValues={{ usage_type: 'stock_issue', usage_date: dayjs().format('YYYY-MM-DD') }}>
            <Form.Item label="Budget Line" name="budget_line" rules={[{ required: true }]}>
              <Select options={(activeBudget ? (budgetLines[activeBudget.id] || []) : []).map((line) => ({ value: line.id, label: line.item_name }))} />
            </Form.Item>
            <Form.Item label="Usage Type" name="usage_type" rules={[{ required: true }]}>
              <Select
                options={[
                  { value: 'stock_issue', label: 'Stock Issue' },
                  { value: 'service_receipt', label: 'Service Delivery' },
                  { value: 'capex_receipt', label: 'Capex Receipt' },
                  { value: 'journal', label: 'Finance Journal' },
                  { value: 'manual_adjust', label: 'Manual Adjustment' },
                ]}
              />
            </Form.Item>
            <Form.Item label="Usage Date" name="usage_date" rules={[{ required: true }]}>
              <Input type="date" />
            </Form.Item>
            <Form.Item label="Quantity" name="quantity">
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item label="Amount" name="amount" rules={[{ required: true }]}>
              <Input type="number" min={0} step={0.01} />
            </Form.Item>
            <Form.Item label="Reference Type" name="reference_type" rules={[{ required: true }]}>
              <Input placeholder="e.g. PO" />
            </Form.Item>
            <Form.Item label="Reference ID" name="reference_id" rules={[{ required: true }]}>
              <Input placeholder="Document number" />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </Spin>
  );
};

export default BudgetingWorkspace;
