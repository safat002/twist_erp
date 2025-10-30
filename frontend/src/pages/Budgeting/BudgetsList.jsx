import React, { useEffect, useMemo, useState } from 'react';
import { Card, DatePicker, Input, Select, Space, Spin, Table, Tag, Typography, message } from 'antd';
import dayjs from 'dayjs';

import { fetchBudgets } from '../../services/budget';
import { useCompany } from '../../contexts/CompanyContext';

const { Title } = Typography;

const STATUS_COLORS = {
  DRAFT: 'default',
  PROPOSED: 'geekblue',
  UNDER_REVIEW: 'purple',
  ACTIVE: 'green',
  LOCKED: 'gold',
  CLOSED: 'magenta',
  ARCHIVED: 'red',
};

const BudgetsList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [period, setPeriod] = useState([dayjs().startOf('year'), dayjs().endOf('year')]);

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
        if (statusFilter !== 'all' && row.status !== statusFilter) {
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

  const columns = [
    {
      title: 'Budget',
      dataIndex: 'name',
      key: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <span>{value || 'Untitled Budget'}</span>
          <span style={{ color: '#8c8c8c', fontSize: 12 }}>{record.cost_center_name || record.cost_center}</span>
        </Space>
      ),
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
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => <Tag color={STATUS_COLORS[value] || 'default'}>{value}</Tag>,
    },
  ];

  return (
    <Spin spinning={loading} tip="Loading budgets">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Title level={3} style={{ marginBottom: 0 }}>Budget Registry</Title>
            <span style={{ color: '#8c8c8c' }}>
              {currentCompany ? currentCompany.name + ' · ' + currentCompany.code : 'Select a company to view budgets'}
            </span>
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
                { value: 'all', label: 'All statuses' },
                { value: 'DRAFT', label: 'Draft' },
                { value: 'PROPOSED', label: 'Proposed' },
                { value: 'UNDER_REVIEW', label: 'Under review' },
                { value: 'ACTIVE', label: 'Active' },
                { value: 'LOCKED', label: 'Locked' },
                { value: 'CLOSED', label: 'Closed' },
                { value: 'ARCHIVED', label: 'Archived' },
              ]}
            />
            <DatePicker.RangePicker
              value={period}
              onChange={(value) => setPeriod(value)}
              allowEmpty={[false, false]}
            />
          </Space>
          <Table columns={columns} dataSource={dataSource} pagination={{ pageSize: 12 }} />
        </Space>
      </Card>
    </Spin>
  );
};

export default BudgetsList;
