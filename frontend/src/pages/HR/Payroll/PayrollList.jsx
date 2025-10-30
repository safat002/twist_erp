import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  CheckCircleOutlined,
  DollarCircleOutlined,
  ExclamationCircleOutlined,
  FileSearchOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import {
  cancelPayrollRun,
  createPayrollRun,
  fetchPayrollRuns,
  finalizePayrollRun,
} from '../../../services/hr';
import api from '../../../services/api';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const PAYROLL_STATUS_BADGES = {
  DRAFT: { label: 'Draft', color: 'default', icon: <FileSearchOutlined /> },
  COMPUTED: { label: 'Computed', color: 'blue', icon: <ApartmentOutlined /> },
  APPROVED: { label: 'Approved', color: 'green', icon: <CheckCircleOutlined /> },
  POSTED: { label: 'Posted', color: 'cyan', icon: <DollarCircleOutlined /> },
  CANCELLED: { label: 'Cancelled', color: 'red', icon: <ExclamationCircleOutlined /> },
};

const DEMO_PAYROLL_RUNS = [
  {
    id: 'demo-run-1',
    period_start: dayjs().subtract(1, 'month').startOf('month').format('YYYY-MM-DD'),
    period_end: dayjs().subtract(1, 'month').endOf('month').format('YYYY-MM-DD'),
    period_label: dayjs().subtract(1, 'month').format('MMMM YYYY'),
    status: 'POSTED',
    gross_total: 4200000,
    deduction_total: 420000,
    net_total: 3780000,
    lines: [
      {
        id: 'demo-line-1',
        employee_name: 'Farhana Rahman',
        employee_code: 'EMP-1001',
        department_name: 'People Operations',
        base_pay: 180000,
        allowance_total: 60000,
        overtime_pay: 15000,
        gross_pay: 255000,
        deduction_total: 25500,
        net_pay: 229500,
      },
    ],
  },
  {
    id: 'demo-run-2',
    period_start: dayjs().startOf('month').format('YYYY-MM-DD'),
    period_end: dayjs().endOf('month').format('YYYY-MM-DD'),
    period_label: dayjs().format('MMMM YYYY'),
    status: 'COMPUTED',
    gross_total: 4370000,
    deduction_total: 437000,
    net_total: 3933000,
    lines: [],
  },
];

const formatCurrency = (value, currency = 'BDT') =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(Number(value || 0));

export default function PayrollList() {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [runs, setRuns] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [isCreateModalVisible, setCreateModalVisible] = useState(false);
  const [isFinalizeModalVisible, setFinalizeModalVisible] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [createForm] = Form.useForm();
  const [finalizeForm] = Form.useForm();

  const isDemoCompany = !currentCompany || Number.isNaN(Number(currentCompany.id));

  const loadAccounts = async () => {
    if (accounts.length > 0 || isDemoCompany) {
      return;
    }
    try {
      const response = await api.get('/api/v1/finance/accounts/');
      const payload = response?.data;
      const list = Array.isArray(payload?.results) ? payload.results : Array.isArray(payload) ? payload : [];
      setAccounts(list);
    } catch (error) {
      console.warn('Unable to load accounts for payroll finalisation.', error);
      message.warning('Unable to load account list. Please refresh before finalising payroll.');
    }
  };

  const loadRuns = async () => {
    if (!currentCompany) {
      return;
    }
    setLoading(true);
    try {
      if (isDemoCompany) {
        setRuns(DEMO_PAYROLL_RUNS);
        return;
      }
      const data = await fetchPayrollRuns();
      setRuns(Array.isArray(data) ? data : []);
    } catch (error) {
      console.warn('Unable to load payroll runs. Showing demo data.', error);
      setRuns(DEMO_PAYROLL_RUNS);
      message.warning('Showing demo payroll data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentCompany?.id]);

  const openCreateModal = () => {
    createForm.resetFields();
    createForm.setFieldsValue({
      period: [dayjs().startOf('month'), dayjs().endOf('month')],
    });
    if (!isDemoCompany) {
      loadAccounts();
    }
    setCreateModalVisible(true);
  };

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      const [start, end] = values.period || [];
      const payload = {
        period_start: start?.format('YYYY-MM-DD'),
        period_end: end?.format('YYYY-MM-DD'),
        period_label: values.period_label,
        notes: values.notes,
      };

      if (values.expense_account) {
        payload.expense_account = values.expense_account;
      }
      if (values.liability_account) {
        payload.liability_account = values.liability_account;
      }

      if (isDemoCompany) {
        const newRun = {
          id: `demo-run-${Date.now()}`,
          status: 'COMPUTED',
          gross_total: 0,
          deduction_total: 0,
          net_total: 0,
          lines: [],
          ...payload,
        };
        setRuns((prev) => [newRun, ...prev]);
        message.success('Payroll run generated (demo)');
        setCreateModalVisible(false);
        return;
      }

      const created = await createPayrollRun(payload);
      setRuns((prev) => [created, ...prev]);
      message.success('Payroll run generated');
      setCreateModalVisible(false);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      console.warn('Payroll run creation failed:', error);
      message.error(error?.response?.data?.detail || 'Unable to generate payroll run.');
    }
  };

  const openFinalizeModal = async (run) => {
    setSelectedRun(run);
    setFinalizeModalVisible(true);
    finalizeForm.resetFields();
    finalizeForm.setFieldsValue({
      expense_account: run.expense_account || run.expense_account_id || null,
      liability_account: run.liability_account || run.liability_account_id || null,
      post_to_finance: true,
    });
    await loadAccounts();
  };

  const handleFinalize = async () => {
    try {
      const values = await finalizeForm.validateFields();
      if (!selectedRun) {
        message.error('Select a payroll run first.');
        return;
      }

      if (isDemoCompany) {
        setRuns((prev) =>
          prev.map((run) =>
            run.id === selectedRun.id
              ? {
                  ...run,
                  status: values.post_to_finance ? 'POSTED' : 'APPROVED',
                }
              : run,
          ),
        );
        message.success('Payroll run finalised (demo)');
        setFinalizeModalVisible(false);
        return;
      }

      const payload = {
        expense_account: values.expense_account,
        liability_account: values.liability_account,
        post_to_finance: values.post_to_finance,
      };
      const updated = await finalizePayrollRun(selectedRun.id, payload);
      setRuns((prev) => prev.map((run) => (run.id === updated.id ? updated : run)));
      message.success('Payroll run finalised');
      setFinalizeModalVisible(false);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      console.warn('Payroll finalisation failed:', error);
      message.error(error?.response?.data?.detail || 'Unable to finalise payroll run.');
    }
  };

  const handleCancelRun = async (run) => {
    if (isDemoCompany) {
      setRuns((prev) => prev.filter((item) => item.id !== run.id));
      message.info('Payroll run removed (demo)');
      return;
    }
    try {
      await cancelPayrollRun(run.id);
      setRuns((prev) =>
        prev.map((item) => (item.id === run.id ? { ...item, status: 'CANCELLED' } : item)),
      );
      message.success('Payroll run cancelled');
    } catch (error) {
      console.warn('Unable to cancel payroll run:', error);
      message.error(error?.response?.data?.detail || 'Unable to cancel payroll run.');
    }
  };

  const accountOptions = useMemo(
    () =>
      accounts.map((account) => ({
        label: `${account.code} – ${account.name}`,
        value: account.id,
      })),
    [accounts],
  );

  const columns = useMemo(
    () => [
      {
        title: 'Period',
        dataIndex: 'period_label',
        key: 'period_label',
        render: (value, record) => value || `${record.period_start} → ${record.period_end}`,
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (value) => {
          const badge = PAYROLL_STATUS_BADGES[value] || { label: value, color: 'default' };
          return <Tag color={badge.color}>{badge.label}</Tag>;
        },
      },
      {
        title: 'Gross',
        dataIndex: 'gross_total',
        key: 'gross_total',
        align: 'right',
        render: (value) => formatCurrency(value),
      },
      {
        title: 'Deduction',
        dataIndex: 'deduction_total',
        key: 'deduction_total',
        align: 'right',
        render: (value) => formatCurrency(value),
      },
      {
        title: 'Net Pay',
        dataIndex: 'net_total',
        key: 'net_total',
        align: 'right',
        render: (value) => formatCurrency(value),
      },
      {
        title: 'Actions',
        key: 'actions',
        width: 220,
        render: (_, record) => (
          <Space>
            <Button size="small" onClick={() => openFinalizeModal(record)} disabled={record.status === 'POSTED'}>
              Finalise
            </Button>
            <Button
              size="small"
              danger
              disabled={record.status === 'POSTED' || record.status === 'CANCELLED'}
              onClick={() => handleCancelRun(record)}
            >
              Cancel
            </Button>
          </Space>
        ),
      },
    ],
    [],
  );

  const lineColumns = [
    {
      title: 'Employee',
      dataIndex: 'employee_name',
      key: 'employee_name',
      render: (value, record) => `${record.employee_code || ''} ${value}`.trim(),
    },
    {
      title: 'Department',
      dataIndex: 'department_name',
      key: 'department_name',
    },
    {
      title: 'Base',
      dataIndex: 'base_pay',
      key: 'base_pay',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Allowance',
      dataIndex: 'allowance_total',
      key: 'allowance_total',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Overtime',
      dataIndex: 'overtime_pay',
      key: 'overtime_pay',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Gross',
      dataIndex: 'gross_pay',
      key: 'gross_pay',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Deduction',
      dataIndex: 'deduction_total',
      key: 'deduction_total',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
    {
      title: 'Net',
      dataIndex: 'net_pay',
      key: 'net_pay',
      align: 'right',
      render: (value) => formatCurrency(value),
    },
  ];

  return (
    <Card
      title="Payroll Runs"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadRuns} loading={loading}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            Generate Payroll
          </Button>
        </Space>
      }
    >
      <Table
        rowKey={(record) => record.id}
        dataSource={runs}
        columns={columns}
        loading={loading}
        pagination={{ pageSize: 8 }}
        expandable={{
          expandedRowRender: (record) => (
            <div>
              <Text strong style={{ marginBottom: 12, display: 'block' }}>
                Payroll Lines
              </Text>
              <Table
                rowKey={(line) => line.id || `${line.employee}-${record.id}`}
                columns={lineColumns}
                dataSource={Array.isArray(record.lines) ? record.lines : []}
                size="small"
                pagination={false}
              />
            </div>
          ),
          rowExpandable: (record) => Array.isArray(record.lines) && record.lines.length > 0,
        }}
      />

      <Modal
        open={isCreateModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={handleCreate}
        title="Generate Payroll Run"
        okText="Generate"
        destroyOnClose
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            label="Payroll Period"
            name="period"
            rules={[{ required: true, message: 'Select payroll period.' }]}
          >
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="Label" name="period_label">
            <Input placeholder="e.g. September 2025" />
          </Form.Item>
          <Form.Item label="Notes" name="notes">
            <Input.TextArea rows={3} placeholder="Payroll preparation notes (optional)" />
          </Form.Item>
          {!isDemoCompany && (
            <Space size="large" style={{ width: '100%' }}>
              <Form.Item label="Expense Account" name="expense_account" style={{ flex: 1 }}>
                <Select
                  showSearch
                  allowClear
                  placeholder="Optional"
                  options={accountOptions.filter((account) => account.label.includes('Expense'))}
                />
              </Form.Item>
              <Form.Item label="Liability Account" name="liability_account" style={{ flex: 1 }}>
                <Select
                  showSearch
                  allowClear
                  placeholder="Optional"
                  options={accountOptions.filter((account) => account.label.includes('Liability') || account.label.includes('Payable'))}
                />
              </Form.Item>
            </Space>
          )}
        </Form>
      </Modal>

      <Modal
        open={isFinalizeModalVisible}
        onCancel={() => {
          setFinalizeModalVisible(false);
          setSelectedRun(null);
        }}
        onOk={handleFinalize}
        okText="Finalize"
        title={selectedRun ? `Finalize ${selectedRun.period_label || 'Payroll Run'}` : 'Finalize Payroll'}
        destroyOnClose
      >
        <Form
          form={finalizeForm}
          layout="vertical"
          initialValues={{ post_to_finance: true }}
        >
          {!isDemoCompany && (
            <>
              <Form.Item
                label="Expense Account"
                name="expense_account"
                rules={[{ required: true, message: 'Select payroll expense account.' }]}
              >
                <Select
                  options={accountOptions.filter((account) => account.label.includes('Expense'))}
                  showSearch
                  placeholder="Select expense account"
                />
              </Form.Item>
              <Form.Item
                label="Liability Account"
                name="liability_account"
                rules={[{ required: true, message: 'Select payroll liability account.' }]}
              >
                <Select
                  options={accountOptions.filter((account) => account.label.includes('Liability') || account.label.includes('Payable'))}
                  showSearch
                  placeholder="Select liability account"
                />
              </Form.Item>
            </>
          )}

          <Form.Item label="Post journal to Finance" name="post_to_finance">
            <Select
              options={[
                { value: true, label: 'Yes, create & post journal' },
                { value: false, label: 'No, keep as approved only' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
