import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Space,
  Segmented,
  DatePicker,
  Tag,
  Timeline,
  Typography,
  List,
  Badge,
  Tooltip,
} from 'antd';
import {
  SwapRightOutlined,
  TruckOutlined,
  ExclamationCircleOutlined,
  DeploymentUnitOutlined,
  FieldTimeOutlined,
} from '@ant-design/icons';
import { Column } from '@ant-design/charts';
import dayjs from 'dayjs';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const FALLBACK_MOVEMENTS = [
  {
    id: 'MOVE-1001',
    reference: 'GRN-4581',
    type: 'Inbound',
    sku: 'FAB-ROLL-60',
    name: 'Cotton Fabric Roll 60 GSM',
    quantity: 120,
    uom: 'Roll',
    from: 'Supplier: Dhaka Cotton Mills',
    to: 'HQ Distribution',
    status: 'Received',
    timestamp: '2024-06-12 08:45',
    owner: 'Receiving Team',
  },
  {
    id: 'MOVE-1002',
    reference: 'ISS-7732',
    type: 'Outbound',
    sku: 'ZIP-NYLON',
    name: 'Nylon Zipper 18"',
    quantity: 400,
    uom: 'Piece',
    from: 'HQ Distribution',
    to: 'Production Line 3',
    status: 'Staged',
    timestamp: '2024-06-12 09:30',
    owner: 'Kitting Team',
  },
  {
    id: 'MOVE-1003',
    reference: 'TRF-2201',
    type: 'Transfer',
    sku: 'BOX-EXP',
    name: 'Export Carton Box',
    quantity: 600,
    uom: 'Piece',
    from: 'HQ Distribution',
    to: 'Fulfilment Centre',
    status: 'In Transit',
    timestamp: '2024-06-12 11:05',
    owner: 'Logistics',
  },
  {
    id: 'MOVE-1004',
    reference: 'RET-087',
    type: 'Return',
    sku: 'DYE-NVY',
    name: 'Reactive Dye Navy Blue 5kg',
    quantity: 10,
    uom: 'Bucket',
    from: 'Production Line 1',
    to: 'Print Unit Store',
    status: 'Quality Hold',
    timestamp: '2024-06-11 16:40',
    owner: 'QA Team',
  },
];

const FALLBACK_ACTIVITY = [
  { hour: '08:00', inbound: 28, outbound: 21, transfers: 4 },
  { hour: '10:00', inbound: 35, outbound: 33, transfers: 6 },
  { hour: '12:00', inbound: 26, outbound: 30, transfers: 5 },
  { hour: '14:00', inbound: 32, outbound: 28, transfers: 8 },
  { hour: '16:00', inbound: 24, outbound: 26, transfers: 7 },
];

const FALLBACK_TIMELINE = [
  {
    time: '07:45',
    title: 'Dock Door 3 opened for inbound truck',
    type: 'inbound',
  },
  {
    time: '09:10',
    title: 'Wave #27 picking started',
    type: 'outbound',
  },
  {
    time: '11:30',
    title: 'Inter-warehouse transfer scheduled',
    type: 'transfer',
  },
  {
    time: '13:20',
    title: 'Return inspection flagged discrepancy',
    type: 'exception',
  },
  {
    time: '15:00',
    title: 'Courier dispatch for ecommerce orders',
    type: 'outbound',
  },
];

const statusMap = {
  Received: 'green',
  Staged: 'processing',
  'In Transit': 'blue',
  'Quality Hold': 'volcano',
};

const StockMovements = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [movements, setMovements] = useState([]);
  const [movementFilter, setMovementFilter] = useState('ALL');
  const [activity, setActivity] = useState(FALLBACK_ACTIVITY);
  const [timelineEvents, setTimelineEvents] = useState(FALLBACK_TIMELINE);
  const [dateFilter, setDateFilter] = useState([dayjs().startOf('day'), dayjs().endOf('day')]);

  useEffect(() => {
    loadMovements();
  }, [currentCompany, movementFilter, dateFilter]);

  const loadMovements = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setMovements(FALLBACK_MOVEMENTS);
        setActivity(FALLBACK_ACTIVITY);
        setTimelineEvents(FALLBACK_TIMELINE);
        return;
      }
      const response = await api.get('/api/v1/inventory/movements/', {
        params: {
          type: movementFilter === 'ALL' ? undefined : movementFilter,
          date_from: dateFilter?.[0]?.format('YYYY-MM-DD'),
          date_to: dateFilter?.[1]?.format('YYYY-MM-DD'),
        },
      });
      const payload = response.data || {};
      const results = Array.isArray(payload.results) ? payload.results : [];
      setMovements(results);
      if (Array.isArray(payload.activity)) {
        setActivity(payload.activity);
      }
      if (Array.isArray(payload.timeline)) {
        setTimelineEvents(payload.timeline);
      }
    } catch (error) {
      console.warn('Stock movements fallback data used:', error?.message);
      setMovements(FALLBACK_MOVEMENTS);
      setActivity(FALLBACK_ACTIVITY);
      setTimelineEvents(FALLBACK_TIMELINE);
    } finally {
      setLoading(false);
    }
  };

  const filteredMovements = useMemo(() => {
    if (movementFilter === 'ALL') {
      return movements;
    }
    return (movements || []).filter((movement) => movement.type === movementFilter);
  }, [movements, movementFilter]);

  const activityConfig = useMemo(() => {
    const safeData = (Array.isArray(activity) ? activity : []).reduce((acc, item) => {
      acc.push({ hour: item.hour, type: 'Inbound', value: Number(item?.inbound) || 0 });
      acc.push({ hour: item.hour, type: 'Outbound', value: Number(item?.outbound) || 0 });
      acc.push({ hour: item.hour, type: 'Transfer', value: Number(item?.transfers) || 0 });
      return acc;
    }, []);
    return {
      data: safeData,
      xField: 'hour',
      yField: 'value',
      seriesField: 'type',
      isGroup: true,
      color: ({ type }) => {
        if (type === 'Inbound') return '#52c41a';
        if (type === 'Outbound') return '#1890ff';
        return '#faad14';
      },
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${Number(datum.value).toLocaleString()} picks`,
        }),
      },
    };
  }, [activity]);

  const columns = [
    {
      title: 'Reference',
      dataIndex: 'reference',
      key: 'reference',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.id}</Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (value) => (
        <Tag color={value === 'Inbound' ? 'green' : value === 'Outbound' ? 'blue' : value === 'Transfer' ? 'purple' : 'gold'}>
          {value}
        </Tag>
      ),
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">{record.name}</Text>
        </Space>
      ),
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      align: 'right',
      render: (value, record) => `${Number(value || 0).toLocaleString()} ${record.uom || ''}`,
    },
    {
      title: 'From → To',
      key: 'route',
      render: (_, record) => (
        <Space>
          <SwapRightOutlined />
          <Text>{record.from}</Text>
          <Text type="secondary">→</Text>
          <Text>{record.to}</Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value) => (
        <Tag color={statusMap[value] || 'default'}>{value || 'N/A'}</Tag>
      ),
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
    },
    {
      title: 'Owner',
      dataIndex: 'owner',
      key: 'owner',
    },
  ];

  const timelineColor = (type) => {
    if (type === 'inbound') return 'green';
    if (type === 'outbound') return 'blue';
    if (type === 'transfer') return 'purple';
    return 'red';
  };

  return (
    <div>
      <Title level={2}>Stock Movements</Title>
      <Text type="secondary">
        Track inbound, outbound, transfers, and exceptions to keep material flow aligned with the
        Twist ERP inventory playbook.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={8}>
          <Card>
            <Space direction="vertical" size="middle">
              <Segmented
                options={['ALL', 'Inbound', 'Outbound', 'Transfer', 'Return']}
                value={movementFilter}
                onChange={setMovementFilter}
              />
              <RangePicker
                allowClear
                value={dateFilter}
                onChange={(value) => setDateFilter(value)}
              />
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={16}>
          <Card title="Hourly Activity Mix">
            <Column {...activityConfig} height={240} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={16}>
          <Card title="Movement Register" loading={loading}>
            <Table
              dataSource={filteredMovements}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 15 }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Live Timeline" style={{ marginBottom: 16 }}>
            <Timeline
              mode="left"
              items={timelineEvents.map((event) => ({
                color: timelineColor(event.type),
                label: <Text strong>{event.time}</Text>,
                children: (
                  <Space>
                    {event.type === 'inbound' && <TruckOutlined style={{ color: '#52c41a' }} />}
                    {event.type === 'outbound' && <DeploymentUnitOutlined style={{ color: '#1890ff' }} />}
                    {event.type === 'transfer' && <FieldTimeOutlined style={{ color: '#722ed1' }} />}
                    {event.type === 'exception' && <ExclamationCircleOutlined style={{ color: '#f5222d' }} />}
                    <Text>{event.title}</Text>
                  </Space>
                ),
              }))}
            />
          </Card>
          <Card title="Exception Queue">
            <List
              dataSource={filteredMovements.filter((item) => item.status === 'Quality Hold')}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space>
                    <Badge status="error" />
                    <Space direction="vertical" size={0}>
                      <Text strong>{item.reference}</Text>
                      <Text type="secondary">{item.sku} · {item.timestamp}</Text>
                    </Space>
                  </Space>
                </List.Item>
              )}
              locale={{ emptyText: 'No quality holds right now.' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default StockMovements;
