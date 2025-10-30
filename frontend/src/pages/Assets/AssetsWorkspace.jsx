import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Space,
  Tag,
  Button,
  List,
  Timeline,
  Tabs,
  Progress,
  Typography,
} from 'antd';
import {
  ToolOutlined,
  AlertOutlined,
  CalendarOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
  DeploymentUnitOutlined,
  PlusOutlined,
  ArrowUpOutlined,
} from '@ant-design/icons';
import { Area, Column } from '@ant-design/charts';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useCompany } from '../../contexts/CompanyContext';
import api from '../../services/api';

const { Title, Paragraph, Text } = Typography;

const INITIAL_KPIS = [
  { key: 'book_value', label: 'Book Value', value: 18450000, suffix: 'BDT', trend: 6 },
  { key: 'active_assets', label: 'Active Assets', value: 426, suffix: '', trend: 4 },
  { key: 'utilization', label: 'Utilization Rate', value: 82, suffix: '%', trend: 3 },
  { key: 'maintenance', label: 'Maintenance Backlog', value: 9, suffix: 'Jobs', trend: -12 },
];

const INITIAL_DEPRECIATION = [
  { month: 'Jan', opening: 19.2, depreciation: 0.6 },
  { month: 'Feb', opening: 18.6, depreciation: 0.6 },
  { month: 'Mar', opening: 18.0, depreciation: 0.6 },
  { month: 'Apr', opening: 17.5, depreciation: 0.58 },
  { month: 'May', opening: 16.9, depreciation: 0.58 },
  { month: 'Jun', opening: 16.3, depreciation: 0.58 },
];

const INITIAL_UTILIZATION = [
  { category: 'Production', value: 88 },
  { category: 'Logistics', value: 76 },
  { category: 'Facilities', value: 64 },
  { category: 'IT Infrastructure', value: 92 },
];

const INITIAL_LIFECYCLE_BOARD = {
  columns: {
    planning: {
      id: 'planning',
      title: 'Planning',
      description: 'Capex approvals & sourcing',
      itemIds: ['asset-301', 'asset-302'],
    },
    commissioning: {
      id: 'commissioning',
      title: 'Commissioning',
      description: 'Being deployed on site',
      itemIds: ['asset-210'],
    },
    operational: {
      id: 'operational',
      title: 'In Service',
      description: 'Active & productive assets',
      itemIds: ['asset-111', 'asset-114', 'asset-118'],
    },
    retirement: {
      id: 'retirement',
      title: 'Retirement',
      description: 'Under disposal or auction',
      itemIds: ['asset-018'],
    },
  },
  items: {
    'asset-301': {
      id: 'asset-301',
      tag: 'CAPEX-2025-014',
      title: 'Cutting Machine CX-11',
      owner: 'Facilities',
      status: 'Budget Review',
    },
    'asset-302': {
      id: 'asset-302',
      tag: 'CAPEX-2025-019',
      title: 'Solar Array Phase 2',
      owner: 'Sustainability',
      status: 'Specs finalizing',
    },
    'asset-210': {
      id: 'asset-210',
      tag: 'EQ-872',
      title: 'Digital Printer Line 4',
      owner: 'Print Unit',
      status: 'Awaiting calibration',
    },
    'asset-111': {
      id: 'asset-111',
      tag: 'EQ-221',
      title: 'ERP Core Servers',
      owner: 'IT Ops',
      status: 'Running 24/7',
    },
    'asset-114': {
      id: 'asset-114',
      tag: 'VEH-012',
      title: 'Logistics Van 6',
      owner: 'Fleet',
      status: 'Telemetry healthy',
    },
    'asset-118': {
      id: 'asset-118',
      tag: 'EQ-412',
      title: 'Embroidery Machine A-3',
      owner: 'Production',
      status: 'High utilization',
    },
    'asset-018': {
      id: 'asset-018',
      tag: 'EQ-098',
      title: 'Legacy Boiler',
      owner: 'Facilities',
      status: 'Auction scheduled',
    },
  },
};

const INITIAL_MAINTENANCE = [
  {
    id: 'maint-1',
    asset: 'Embroidery Machine A-3',
    window: '26 Oct · 10:00',
    supervisor: 'Salma Rahman',
    tasks: ['Lubrication', 'Firmware update'],
  },
  {
    id: 'maint-2',
    asset: 'Logistics Van 6',
    window: '27 Oct · 09:00',
    supervisor: 'Fleet Ops',
    tasks: ['Tyre rotation', 'Brake calibration'],
  },
  {
    id: 'maint-3',
    asset: 'Digital Printer Line 4',
    window: '29 Oct · 14:00',
    supervisor: 'Print Engineering',
    tasks: ['Calibration', 'Nozzle inspection'],
  },
];

const INITIAL_ALERTS = [
  {
    id: 'alert-1',
    message: 'Asset EQ-221 exceeded vibration threshold',
    severity: 'critical',
  },
  {
    id: 'alert-2',
    message: 'Warranty expiring for 12 assets within 30 days',
    severity: 'warning',
  },
  {
    id: 'alert-3',
    message: 'Insurance certificate pending renewal',
    severity: 'info',
  },
];

const INITIAL_AUTOMATIONS = [
  {
    id: 'auto-1',
    title: 'Schedule predictive maintenance',
    detail: 'IoT signal > threshold triggers work order',
    status: 'active',
  },
  {
    id: 'auto-2',
    title: 'Auto-post depreciation batch',
    detail: 'JournalEntryService posts monthly entries',
    status: 'active',
  },
  {
    id: 'auto-3',
    title: 'Asset onboarding checklist',
    detail: 'Drag-and-drop workflow for new equipment',
    status: 'beta',
  },
];

const severityColors = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};

const AssetsWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState(INITIAL_KPIS);
  const [depreciationTrend, setDepreciationTrend] = useState(INITIAL_DEPRECIATION);
  const [utilizationBreakdown, setUtilizationBreakdown] = useState(INITIAL_UTILIZATION);
  const [lifecycleBoard, setLifecycleBoard] = useState(INITIAL_LIFECYCLE_BOARD);
  const [maintenanceSchedule, setMaintenanceSchedule] = useState(INITIAL_MAINTENANCE);
  const [assetAlerts, setAssetAlerts] = useState(INITIAL_ALERTS);
  const [automations, setAutomations] = useState(INITIAL_AUTOMATIONS);

  useEffect(() => {
    const fetchOverview = async () => {
      setLoading(true);
      try {
        const response = await api.get('/api/v1/assets/overview/', {
          params: { company: currentCompany?.id },
        });
        const payload = response.data || {};

        if (Array.isArray(payload.kpis) && payload.kpis.length) {
          setKpis(payload.kpis);
        } else {
          setKpis(INITIAL_KPIS);
        }

        setDepreciationTrend(
          Array.isArray(payload.depreciation_trend) && payload.depreciation_trend.length
            ? payload.depreciation_trend
            : INITIAL_DEPRECIATION,
        );

        setUtilizationBreakdown(
          Array.isArray(payload.utilization) && payload.utilization.length
            ? payload.utilization
            : INITIAL_UTILIZATION,
        );

        if (
          payload.lifecycle_board &&
          payload.lifecycle_board.columns &&
          payload.lifecycle_board.items
        ) {
          setLifecycleBoard(payload.lifecycle_board);
        } else {
          setLifecycleBoard(JSON.parse(JSON.stringify(INITIAL_LIFECYCLE_BOARD)));
        }

        setMaintenanceSchedule(
          Array.isArray(payload.maintenance_schedule) && payload.maintenance_schedule.length
            ? payload.maintenance_schedule
            : INITIAL_MAINTENANCE,
        );

        setAssetAlerts(
          Array.isArray(payload.alerts) && payload.alerts.length ? payload.alerts : INITIAL_ALERTS,
        );

        setAutomations(
          Array.isArray(payload.automations) && payload.automations.length
            ? payload.automations
            : INITIAL_AUTOMATIONS,
        );
      } catch (error) {
        console.warn('Asset overview fallback data used:', error?.message);
        setKpis(INITIAL_KPIS);
        setDepreciationTrend(INITIAL_DEPRECIATION);
        setUtilizationBreakdown(INITIAL_UTILIZATION);
        setLifecycleBoard(JSON.parse(JSON.stringify(INITIAL_LIFECYCLE_BOARD)));
        setMaintenanceSchedule(INITIAL_MAINTENANCE);
        setAssetAlerts(INITIAL_ALERTS);
        setAutomations(INITIAL_AUTOMATIONS);
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, [currentCompany?.id]);

  const depreciationConfig = useMemo(() => {
    const data = Array.isArray(depreciationTrend)
      ? depreciationTrend.reduce((acc, item) => {
          acc.push({
            month: item.month,
            type: 'Opening Value',
            value: Number(item.opening) || 0,
          });
          acc.push({
            month: item.month,
            type: 'Depreciation',
            value: Number(item.depreciation) || 0,
          });
          return acc;
        }, [])
      : [];

    return {
      data,
      xField: 'month',
      yField: 'value',
      seriesField: 'type',
      isGroup: true,
      columnStyle: { radius: [8, 8, 0, 0] },
      color: ({ type }) => (type === 'Opening Value' ? '#1890ff' : '#faad14'),
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${datum.value.toFixed(2)} M`,
        }),
      },
    };
  }, [depreciationTrend]);

  const utilizationConfig = useMemo(() => {
    const data = (Array.isArray(utilizationBreakdown) ? utilizationBreakdown : []).map((item) => ({
      ...item,
      value: Number(item?.value) || 0,
    }));

    return {
      data,
      xField: 'category',
      yField: 'value',
      columnStyle: { radius: [10, 10, 0, 0] },
      color: '#52c41a',
      tooltip: {
        formatter: (datum) => ({
          name: datum.category,
          value: `${datum.value}% utilized`,
        }),
      },
    };
  }, [utilizationBreakdown]);

  const handleDragEnd = (result) => {
    const { destination, source, draggableId } = result;
    if (!destination) {
      return;
    }
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    setLifecycleBoard((prev) => {
      const startColumn = prev.columns[source.droppableId];
      const finishColumn = prev.columns[destination.droppableId];

      if (!startColumn || !finishColumn) {
        return prev;
      }

      if (startColumn === finishColumn) {
        const newItemIds = Array.from(startColumn.itemIds);
        newItemIds.splice(source.index, 1);
        newItemIds.splice(destination.index, 0, draggableId);

        return {
          ...prev,
          columns: {
            ...prev.columns,
            [startColumn.id]: {
              ...startColumn,
              itemIds: newItemIds,
            },
          },
        };
      }

      const startItemIds = Array.from(startColumn.itemIds);
      startItemIds.splice(source.index, 1);
      const finishItemIds = Array.from(finishColumn.itemIds);
      finishItemIds.splice(destination.index, 0, draggableId);

      return {
        ...prev,
        columns: {
          ...prev.columns,
          [startColumn.id]: {
            ...startColumn,
            itemIds: startItemIds,
          },
          [finishColumn.id]: {
            ...finishColumn,
            itemIds: finishItemIds,
          },
        },
      };
    });
  };

  return (
    <div>
      <Title level={2}>
        Asset Command Center{' '}
        {currentCompany?.name ? <Text type="secondary">· {currentCompany.name}</Text> : null}
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 780 }}>
        Track capitalization, utilization, and maintenance in one intuitive workspace. Drag and drop
        assets across lifecycle stages, monitor predictive maintenance, and mirror finance postings
        for depreciation and valuation.
      </Paragraph>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {kpis.map((item) => (
          <Col key={item.key} xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Space direction="vertical" size={4}>
                <Text type="secondary">{item.label}</Text>
                <Statistic
                  value={item.value}
                  suffix={item.suffix}
                  precision={item.key === 'utilization' ? 1 : 0}
                  prefix={item.key === 'book_value' ? '৳' : undefined}
                  valueStyle={{ fontSize: 24 }}
                />
                <Space size={4}>
                  {item.trend >= 0 ? (
                    <ArrowUpOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <AlertOutlined style={{ color: '#f5222d' }} />
                  )}
                  <Text type={item.trend >= 0 ? 'success' : 'danger'}>
                    {item.trend > 0 ? '+' : ''}
                    {item.trend}%
                  </Text>
                  <Text type="secondary">vs last quarter</Text>
                </Space>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={14}>
          <Card
            title="Depreciation vs Opening Value"
            extra={
              <Space>
                <Button size="small" icon={<ThunderboltOutlined />}>
                  Auto-post batch
                </Button>
                <Button size="small" icon={<PlusOutlined />} type="primary">
                  New Asset
                </Button>
              </Space>
            }
            loading={loading}
          >
            <Column {...depreciationConfig} height={280} />
          </Card>
        </Col>
        <Col xs={24} md={10}>
          <Card title="Utilization by Category" loading={loading}>
            <Column {...utilizationConfig} height={280} />
          </Card>
          <Card title="Compliance & Alerts" style={{ marginTop: 16 }} loading={loading}>
            <List
              dataSource={assetAlerts}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space>
                    <AlertOutlined style={{ color: severityColors[item.severity] || '#1890ff' }} />
                    <Text>{item.message}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Asset Lifecycle Board"
        style={{ marginTop: 16 }}
        extra={<Text type="secondary">Drag assets to update lifecycle status</Text>}
      >
        <DragDropContext onDragEnd={handleDragEnd}>
          <Row gutter={[16, 16]}>
            {Object.values(lifecycleBoard.columns).map((column) => (
              <Col key={column.id} xs={24} md={12} xl={6}>
                <Card
                  title={
                    <Space>
                      <ToolOutlined />
                      {column.title}
                      <Tag color="blue">{column.itemIds.length}</Tag>
                    </Space>
                  }
                  extra={<Text type="secondary">{column.description}</Text>}
                  bodyStyle={{ padding: 12, minHeight: 260 }}
                >
                  <Droppable droppableId={column.id}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        style={{
                          minHeight: 220,
                          background: snapshot.isDraggingOver ? '#f0f5ff' : 'transparent',
                          borderRadius: 8,
                          padding: 4,
                          transition: 'background-color 0.2s ease',
                        }}
                      >
                        {column.itemIds.map((itemId, index) => {
                          const card = lifecycleBoard.items[itemId];
                          if (!card) {
                            return null;
                          }
                          return (
                            <Draggable draggableId={card.id} index={index} key={card.id}>
                              {(dragProvided, dragSnapshot) => (
                                <Card
                                  size="small"
                                  ref={dragProvided.innerRef}
                                  {...dragProvided.draggableProps}
                                  {...dragProvided.dragHandleProps}
                                  style={{
                                    marginBottom: 8,
                                    border: '1px solid #f0f0f0',
                                    boxShadow: dragSnapshot.isDragging
                                      ? '0 8px 16px rgba(24, 144, 255, 0.25)'
                                      : '0 1px 3px rgba(0,0,0,0.08)',
                                  }}
                                >
                                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                                    <Space
                                      style={{ justifyContent: 'space-between', width: '100%' }}
                                    >
                                      <Text strong>{card.title}</Text>
                                      <Tag color="purple">{card.owner}</Tag>
                                    </Space>
                                    <Text type="secondary">{card.tag}</Text>
                                    <Text type="secondary">{card.status}</Text>
                                  </Space>
                                </Card>
                              )}
                            </Draggable>
                          );
                        })}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </Card>
              </Col>
            ))}
          </Row>
        </DragDropContext>
      </Card>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={12}>
          <Card
            title="Maintenance Schedule"
            extra={<Button icon={<CalendarOutlined />}>View Calendar</Button>}
            loading={loading}
          >
            <Timeline
              items={maintenanceSchedule.map((item) => ({
                color: '#1890ff',
                children: (
                  <Space direction="vertical" size={0}>
                    <Text strong>{item.asset}</Text>
                    <Text type="secondary">
                      {item.window} · Supervisor: {item.supervisor}
                    </Text>
                    <Text type="secondary">{item.tasks.join(' · ')}</Text>
                  </Space>
                ),
              }))}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="Automation Recipes" loading={loading}>
            <List
              dataSource={automations}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <ThunderboltOutlined style={{ color: '#722ed1' }} />
                      <Text strong>{item.title}</Text>
                      <Tag color={item.status === 'active' ? 'green' : 'blue'}>
                        {item.status.toUpperCase()}
                      </Tag>
                    </Space>
                    <Text type="secondary">{item.detail}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
          <Card title="Compliance Dashboard" style={{ marginTop: 16 }} loading={loading}>
            <Tabs
              defaultActiveKey="certs"
              items={[
                {
                  key: 'certs',
                  label: 'Certificates',
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <ApartmentOutlined style={{ color: '#1890ff' }} />
                        <Text strong>Insurance Coverage</Text>
                      </Space>
                      <Progress percent={92} status="active" />
                      <Space>
                        <ApartmentOutlined style={{ color: '#faad14' }} />
                        <Text strong>Warranty Compliance</Text>
                      </Space>
                      <Progress percent={68} status="exception" />
                    </Space>
                  ),
                },
                {
                  key: 'audits',
                  label: 'Upcoming Audits',
                  children: (
                    <List
                      size="small"
                      dataSource={[
                        { id: 'audit-1', title: 'Fixed Asset Verification', due: '30 Oct' },
                        { id: 'audit-2', title: 'IT Assets Pen-Test', due: '05 Nov' },
                      ]}
                      renderItem={(item) => (
                        <List.Item key={item.id}>
                          <Space>
                            <DeploymentUnitOutlined style={{ color: '#52c41a' }} />
                            <Text>{item.title}</Text>
                            <Tag color="blue">{item.due}</Tag>
                          </Space>
                        </List.Item>
                      )}
                    />
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AssetsWorkspace;
