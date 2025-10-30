import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Col,
  Empty,
  Progress,
  Row,
  Segmented,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { Column } from '@ant-design/plots';

import { fetchBudgets } from '../../services/budget';
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

const formatCurrency = (value) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value ?? '0';
  }
  return numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const formatStatusLabel = (status) => {
  if (!status) {
    return 'Unspecified';
  }
  if (status === 'ALL') {
    return 'All';
  }
  return status
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const BudgetMonitor = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const { data } = await fetchBudgets();
        setRows(data?.results || data || []);
      } catch (error) {
        console.error('Failed to load budgets', error);
        message.error(error?.response?.data?.detail || 'Unable to load budget monitor');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const statusOptions = useMemo(() => {
    const unique = Array.from(new Set(rows.map((row) => row.status).filter(Boolean)));
    return ['ALL', ...unique];
  }, [rows]);

  const filteredRows = useMemo(
    () => (statusFilter === 'ALL' ? rows : rows.filter((row) => row.status === statusFilter)),
    [rows, statusFilter],
  );

  const progressData = useMemo(
    () =>
      filteredRows.map((row) => ({
        name: row.name || `Budget ${row.id}`,
        value: Number(row.consumed || 0),
        limit: Number(row.amount || 0),
        status: row.status,
      })),
    [filteredRows],
  );

  const chartData = useMemo(
    () =>
      filteredRows.flatMap((row) => {
        const consumed = Number(row.consumed || 0);
        const total = Number(row.amount || 0);
        const remaining = Math.max(total - consumed, 0);
        const budgetName = row.name || `Budget ${row.id}`;
        return [
          { budget: budgetName, type: 'Consumed', value: consumed },
          { budget: budgetName, type: 'Remaining', value: remaining },
        ];
      }),
    [filteredRows],
  );

  const statusSummary = useMemo(() => {
    const aggregate = rows.reduce((acc, row) => {
      const key = row.status || 'UNSPECIFIED';
      if (!acc[key]) {
        acc[key] = { count: 0, amount: 0 };
      }
      acc[key].count += 1;
      acc[key].amount += Number(row.amount || 0);
      return acc;
    }, {});

    return Object.entries(aggregate).map(([status, data]) => ({
      status,
      count: data.count,
      amount: data.amount,
    }));
  }, [rows]);

  const columns = useMemo(
    () => [
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
        key: 'period',
        render: (_, record) => (
          <Text type="secondary">
            {(record.period_start || '-') + ' to ' + (record.period_end || '-')}
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
          return (
            <Space direction="vertical" size={0}>
              <Progress percent={percent} size="small" status={percent >= 95 ? 'exception' : 'active'} />
              <Text type="secondary">
                {formatCurrency(consumed)} / {formatCurrency(limit)}
              </Text>
            </Space>
          );
        },
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (value) => <Tag color={STATUS_COLORS[value] || 'default'}>{value}</Tag>,
      },
    ],
    [],
  );

  const totalLimit = progressData.reduce((acc, row) => acc + row.limit, 0);
  const totalConsumed = progressData.reduce((acc, row) => acc + row.value, 0);
  const usagePercent = totalLimit > 0 ? Math.round((totalConsumed / totalLimit) * 100) : 0;

  return (
    <Spin spinning={loading} tip="Loading budget monitor">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div>
            <Title level={3} style={{ marginBottom: 0 }}>
              Budget Monitor
            </Title>
            <Text type="secondary">
              {currentCompany ? `${currentCompany.name} - ${currentCompany.code}` : 'Select a company to view analytics'}
            </Text>
          </div>
          {statusOptions.length > 1 && (
            <Segmented
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
              options={statusOptions.map((status) => ({ value: status, label: formatStatusLabel(status) }))}
            />
          )}
        </Space>

        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic title="Total Limit" value={formatCurrency(totalLimit)} />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic title="Consumed" value={formatCurrency(totalConsumed)} />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic title="Utilisation" value={usagePercent} suffix="%" />
            </Card>
          </Col>
        </Row>

        {statusSummary.length > 0 && (
          <Card>
            <Space size="small" wrap>
              {statusSummary.map((item) => (
                <Tag key={item.status} color={STATUS_COLORS[item.status] || 'default'}>
                  {formatStatusLabel(item.status)}: {item.count} | {formatCurrency(item.amount)}
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        <Card title="Budget allocation overview">
          {chartData.length > 0 ? (
            <Column
              data={chartData}
              isStack
              xField="budget"
              yField="value"
              seriesField="type"
              height={280}
              legend={{ position: 'top' }}
              tooltip={{ formatter: (datum) => ({ name: datum.type, value: formatCurrency(datum.value) }) }}
              meta={{ value: { alias: 'Amount' } }}
              label={false}
            />
          ) : (
            <Empty description="No budget data" />
          )}
        </Card>

        <Card title="Budgets">
          <Table rowKey="id" dataSource={filteredRows} columns={columns} pagination={{ pageSize: 10 }} />
        </Card>
      </Space>
    </Spin>
  );
};

export default BudgetMonitor;
