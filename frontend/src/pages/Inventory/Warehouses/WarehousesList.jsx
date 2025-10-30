import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Tag,
  Table,
  Space,
  Progress,
  List,
  Typography,
  Tabs,
} from 'antd';
import {
  EnvironmentOutlined,
  ClusterOutlined,
  ThunderboltOutlined,
  AlertOutlined,
  DeploymentUnitOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { Area } from '@ant-design/charts';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;

const FALLBACK_WAREHOUSES = [
  {
    id: 1,
    name: 'HQ Distribution Centre',
    code: 'WH-HQ',
    type: 'Distribution',
    capacity: 8500,
    occupancy: 81,
    health: 'Stable',
    city: 'Dhaka',
    pending_tasks: 12,
  },
  {
    id: 2,
    name: 'Print Unit Store',
    code: 'WH-PRINT',
    type: 'Production',
    capacity: 4200,
    occupancy: 68,
    health: 'Attention',
    city: 'Gazipur',
    pending_tasks: 7,
  },
  {
    id: 3,
    name: 'Fulfilment Centre',
    code: 'WH-FC',
    type: 'E-commerce',
    capacity: 5600,
    occupancy: 74,
    health: 'Stable',
    city: 'Dhaka',
    pending_tasks: 5,
  },
  {
    id: 4,
    name: 'EU Hub',
    code: 'WH-EU',
    type: 'Distribution',
    capacity: 3900,
    occupancy: 54,
    health: 'Stable',
    city: 'Berlin',
    pending_tasks: 4,
  },
];

const FALLBACK_THROUGHPUT = [
  { day: 'Mon', inbound: 320, outbound: 280 },
  { day: 'Tue', inbound: 360, outbound: 310 },
  { day: 'Wed', inbound: 390, outbound: 330 },
  { day: 'Thu', inbound: 420, outbound: 360 },
  { day: 'Fri', inbound: 380, outbound: 340 },
  { day: 'Sat', inbound: 260, outbound: 290 },
];

const FALLBACK_ENVIRONMENTAL_ALERTS = [
  {
    id: 'env-1',
    location: 'Print Unit Cold Room',
    reading: 'Temperature deviation - +3°C',
    severity: 'critical',
  },
  {
    id: 'env-2',
    location: 'HQ Mezzanine',
    reading: 'Humidity 72%',
    severity: 'warning',
  },
];

const FALLBACK_TASKS = [
  {
    id: 'task-1',
    title: 'Cycle count - Zone B',
    owner: 'Team Delta',
    due: 'Today · 4 PM',
  },
  {
    id: 'task-2',
    title: 'Dock door maintenance',
    owner: 'Facilities',
    due: 'Tomorrow · 10 AM',
  },
  {
    id: 'task-3',
    title: 'Slotting optimization review',
    owner: 'Process Excellence',
    due: 'In 2 days',
  },
];

const WarehousesList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [warehouses, setWarehouses] = useState([]);
  const [throughput, setThroughput] = useState(FALLBACK_THROUGHPUT);
  const [environmentalAlerts, setEnvironmentalAlerts] = useState(FALLBACK_ENVIRONMENTAL_ALERTS);
  const [taskPipeline, setTaskPipeline] = useState(FALLBACK_TASKS);

  useEffect(() => {
    loadWarehouses();
  }, [currentCompany]);

  const loadWarehouses = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setWarehouses(FALLBACK_WAREHOUSES);
        setThroughput(FALLBACK_THROUGHPUT);
        setEnvironmentalAlerts(FALLBACK_ENVIRONMENTAL_ALERTS);
        setTaskPipeline(FALLBACK_TASKS);
        return;
      }
      const response = await api.get('/api/v1/inventory/warehouses/');
      const payload = response.data || {};
      const results = Array.isArray(payload.results) ? payload.results : [];
      setWarehouses(results);
      if (Array.isArray(payload.throughput)) {
        setThroughput(payload.throughput);
      }
      if (Array.isArray(payload.environmental_alerts)) {
        setEnvironmentalAlerts(payload.environmental_alerts);
      }
      if (Array.isArray(payload.task_pipeline)) {
        setTaskPipeline(payload.task_pipeline);
      }
    } catch (error) {
      console.warn('Warehouses fallback data used:', error?.message);
      setWarehouses(FALLBACK_WAREHOUSES);
      setThroughput(FALLBACK_THROUGHPUT);
      setEnvironmentalAlerts(FALLBACK_ENVIRONMENTAL_ALERTS);
      setTaskPipeline(FALLBACK_TASKS);
    } finally {
      setLoading(false);
    }
  };

  const metrics = useMemo(() => {
    const totalCapacity = warehouses.reduce(
      (sum, warehouse) => sum + (Number(warehouse.capacity) || 0),
      0,
    );
    const totalOccupancy =
      warehouses.reduce(
        (sum, warehouse) => sum + ((Number(warehouse.capacity) || 0) * (warehouse.occupancy || 0)),
        0,
      ) / (warehouses.length || 1);
    const alertsCount = environmentalAlerts.length;
    const totalTasks = taskPipeline.length;
    return {
      totalCapacity,
      totalOccupancy: Math.round(totalOccupancy),
      alertsCount,
      totalTasks,
    };
  }, [warehouses, environmentalAlerts, taskPipeline]);

  const throughputConfig = useMemo(() => {
    const safeData = (Array.isArray(throughput) ? throughput : []).reduce((acc, item) => {
      acc.push({ day: item.day, type: 'Inbound', value: Number(item?.inbound) || 0 });
      acc.push({ day: item.day, type: 'Outbound', value: Number(item?.outbound) || 0 });
      return acc;
    }, []);
    return {
      data: safeData,
      xField: 'day',
      yField: 'value',
      seriesField: 'type',
      smooth: true,
      color: ({ type }) => (type === 'Inbound' ? '#52c41a' : '#1890ff'),
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${Number(datum.value).toLocaleString()} units`,
        }),
      },
    };
  }, [throughput]);

  const columns = [
    {
      title: 'Warehouse',
      dataIndex: 'name',
      key: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary">
            {record.code} · {record.city}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: 'Capacity (Pallets)',
      dataIndex: 'capacity',
      key: 'capacity',
      align: 'right',
      render: (value) => Number(value || 0).toLocaleString(),
    },
    {
      title: 'Occupancy',
      dataIndex: 'occupancy',
      key: 'occupancy',
      render: (value) => (
        <Progress percent={Math.round(Number(value) || 0)} size="small" status="active" />
      ),
    },
    {
      title: 'Health',
      dataIndex: 'health',
      key: 'health',
      render: (value) => (
        <Tag color={value === 'Stable' ? 'green' : 'orange'}>{value || 'N/A'}</Tag>
      ),
    },
    {
      title: 'Open Tasks',
      dataIndex: 'pending_tasks',
      key: 'pending_tasks',
      render: (value) => (
        <Tag color={Number(value) > 10 ? 'volcano' : 'blue'}>{value || 0}</Tag>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Warehouses & Network</Title>
      <Text type="secondary">
        Visualize warehouse capacity, throughput, and alerts to keep the network aligned with the
        ERP inventory playbook.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Total Capacity"
              value={metrics.totalCapacity}
              precision={0}
              suffix=" pallets"
              prefix={<ClusterOutlined style={{ color: '#1890ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Avg Occupancy"
              value={metrics.totalOccupancy}
              precision={0}
              suffix="%"
              prefix={<DeploymentUnitOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Environment Alerts"
              value={metrics.alertsCount}
              prefix={<AlertOutlined style={{ color: '#f5222d' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card>
            <Statistic
              title="Tasks in Pipeline"
              value={metrics.totalTasks}
              prefix={<ThunderboltOutlined style={{ color: '#722ed1' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col xs={24} xl={16}>
          <Card title="Warehouse Portfolio" loading={loading}>
            <Table
              dataSource={warehouses}
              columns={columns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
          <Card title="Inbound vs Outbound Throughput" style={{ marginTop: 16 }} loading={loading}>
            <Area {...throughputConfig} height={260} />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Environment & Compliance" style={{ marginBottom: 16 }} loading={loading}>
            <List
              dataSource={environmentalAlerts}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Space>
                      <EnvironmentOutlined style={{ color: '#13c2c2' }} />
                      <Text strong>{item.location}</Text>
                    </Space>
                    <Text>{item.reading}</Text>
                    <Tag color={item.severity === 'critical' ? 'red' : 'orange'}>
                      {item.severity.toUpperCase()}
                    </Tag>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Tabs
            defaultActiveKey="tasks"
            items={[
              {
                key: 'tasks',
                label: 'Tasks',
                children: (
                  <List
                    dataSource={taskPipeline}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space direction="vertical" size={0}>
                          <Text strong>{item.title}</Text>
                          <Text type="secondary">
                            Owner: {item.owner} · {item.due}
                          </Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
              {
                key: 'dispatch',
                label: 'Dispatch Waves',
                children: (
                  <List
                    dataSource={[
                      { id: 'wave-1', title: '08:30 · Export Wave', info: '24 orders · Air' },
                      { id: 'wave-2', title: '13:00 · Local Delivery', info: '18 orders · Van' },
                      { id: 'wave-3', title: '16:00 · Ecommerce', info: '45 parcels · Courier' },
                    ]}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space>
                          <SendOutlined style={{ color: '#1890ff' }} />
                          <Space direction="vertical" size={0}>
                            <Text strong>{item.title}</Text>
                            <Text type="secondary">{item.info}</Text>
                          </Space>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
          />
        </Col>
      </Row>
    </div>
  );
};

export default WarehousesList;
