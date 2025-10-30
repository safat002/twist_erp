import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Space,
  Tag,
  List,
  Timeline,
  Typography,
  Button,
} from 'antd';
import {
  ProjectOutlined,
  DeploymentUnitOutlined,
  RocketOutlined,
  ThunderboltOutlined,
  AlertOutlined,
  TeamOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { Area, Column } from '@ant-design/charts';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useCompany } from '../../contexts/CompanyContext';
import api from '../../services/api';

const { Title, Paragraph, Text } = Typography;

const INITIAL_KPIS = [
  { key: 'active_projects', label: 'Active Projects', value: 18, suffix: '', trend: 2 },
  { key: 'on_track', label: 'On Track', value: 72, suffix: '%', trend: -3 },
  { key: 'velocity', label: 'Sprint Velocity', value: 28, suffix: 'pts', trend: 4 },
  { key: 'budget_burn', label: 'Budget Burn', value: 64, suffix: '%', trend: 5 },
];

const INITIAL_DELIVERY_TREND = [
  { month: 'Jan', type: 'Planned', value: 42 },
  { month: 'Jan', type: 'Delivered', value: 38 },
  { month: 'Feb', type: 'Planned', value: 46 },
  { month: 'Feb', type: 'Delivered', value: 44 },
  { month: 'Mar', type: 'Planned', value: 48 },
  { month: 'Mar', type: 'Delivered', value: 47 },
  { month: 'Apr', type: 'Planned', value: 52 },
  { month: 'Apr', type: 'Delivered', value: 50 },
  { month: 'May', type: 'Planned', value: 55 },
  { month: 'May', type: 'Delivered', value: 54 },
  { month: 'Jun', type: 'Planned', value: 58 },
  { month: 'Jun', type: 'Delivered', value: 56 },
];

const INITIAL_RESOURCE_HEATMAP = [
  { squad: 'Platform', load: 78 },
  { squad: 'Mobile', load: 65 },
  { squad: 'Retail Ops', load: 54 },
  { squad: 'Automation', load: 82 },
  { squad: 'Data/AI', load: 91 },
];

const INITIAL_PROJECT_BOARD = {
  columns: {
    backlog: {
      id: 'backlog',
      title: 'Backlog',
      description: 'Ideas & intake',
      itemIds: ['proj-201', 'proj-204'],
    },
    discovery: {
      id: 'discovery',
      title: 'Discovery / Design',
      description: 'Validating scope & solution',
      itemIds: ['proj-301'],
    },
    delivery: {
      id: 'delivery',
      title: 'Delivery',
      description: 'In execution / sprinting',
      itemIds: ['proj-402', 'proj-405'],
    },
    done: {
      id: 'done',
      title: 'Done',
      description: 'Launched & stabilised',
      itemIds: ['proj-501'],
    },
  },
  items: {
    'proj-201': {
      id: 'proj-201',
      name: 'Supplier Portal Revamp',
      owner: 'Procurement Tech',
      status: 'Business case drafting',
    },
    'proj-204': {
      id: 'proj-204',
      name: 'IoT Loom Analytics',
      owner: 'Data/AI',
      status: 'Value assessment',
    },
    'proj-301': {
      id: 'proj-301',
      name: 'Payroll Automation',
      owner: 'HR Tech',
      status: 'Solution design workshops',
    },
    'proj-402': {
      id: 'proj-402',
      name: 'Retail POS Upgrade',
      owner: 'Retail Ops',
      status: 'Sprint 4/8',
    },
    'proj-405': {
      id: 'proj-405',
      name: 'Inventory Drone Scan',
      owner: 'Innovation Lab',
      status: 'Pilot in Unit 2',
    },
    'proj-501': {
      id: 'proj-501',
      name: 'Finance Close Automation',
      owner: 'Finance Systems',
      status: 'Hypercare phase',
    },
  },
};

const INITIAL_MILESTONES = [
  {
    id: 'mile-1',
    project: 'Retail POS Upgrade',
    date: '28 Oct',
    detail: 'Complete integration testing',
  },
  {
    id: 'mile-2',
    project: 'Payroll Automation',
    date: '02 Nov',
    detail: 'Stakeholder sign-off on blueprint',
  },
  {
    id: 'mile-3',
    project: 'Inventory Drone Scan',
    date: '12 Nov',
    detail: 'Drone calibration & safety audit',
  },
  {
    id: 'mile-4',
    project: 'Supplier Portal Revamp',
    date: '20 Nov',
    detail: 'Present MVP roadmap to ExCo',
  },
];

const INITIAL_RISKS = [
  { id: 'risk-1', title: 'Capex approval pending for IoT analytics', severity: 'warning' },
  { id: 'risk-2', title: 'Retail POS vendor facing supply delay', severity: 'critical' },
  { id: 'risk-3', title: 'Resource clash with HR transformation', severity: 'info' },
];

const INITIAL_AUTOMATIONS = [
  {
    id: 'auto-1',
    title: 'Auto-sync sprint velocity',
    detail: 'Pulls Jira metrics into Twist Projects',
    status: 'active',
  },
  {
    id: 'auto-2',
    title: 'Budget Burn Alerts',
    detail: 'Alert when burn > plan by 5%',
    status: 'active',
  },
  {
    id: 'auto-3',
    title: 'Stakeholder Digest',
    detail: 'Drag components to build project health summary',
    status: 'beta',
  },
];

const severityColors = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};

const ProjectsWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState(INITIAL_KPIS);
  const [deliveryTrend, setDeliveryTrend] = useState(INITIAL_DELIVERY_TREND);
  const [resourceHeatmap, setResourceHeatmap] = useState(INITIAL_RESOURCE_HEATMAP);
  const [board, setBoard] = useState(INITIAL_PROJECT_BOARD);
  const [milestones, setMilestones] = useState(INITIAL_MILESTONES);
  const [risks, setRisks] = useState(INITIAL_RISKS);
  const [automations, setAutomations] = useState(INITIAL_AUTOMATIONS);

  useEffect(() => {
    const fetchOverview = async () => {
      setLoading(true);
      try {
        const response = await api.get('/api/v1/projects/overview/', {
          params: { company: currentCompany?.id },
        });
        const payload = response.data || {};

        if (Array.isArray(payload.kpis) && payload.kpis.length) {
          setKpis(payload.kpis);
        } else {
          setKpis(INITIAL_KPIS);
        }

        setDeliveryTrend(
          Array.isArray(payload.delivery_trend) && payload.delivery_trend.length
            ? payload.delivery_trend
            : INITIAL_DELIVERY_TREND,
        );

        setResourceHeatmap(
          Array.isArray(payload.resource_load) && payload.resource_load.length
            ? payload.resource_load
            : INITIAL_RESOURCE_HEATMAP,
        );

        if (payload.board && payload.board.columns && payload.board.items) {
          setBoard(payload.board);
        } else {
          setBoard(JSON.parse(JSON.stringify(INITIAL_PROJECT_BOARD)));
        }

        setMilestones(
          Array.isArray(payload.milestones) && payload.milestones.length
            ? payload.milestones
            : INITIAL_MILESTONES,
        );

        setRisks(
          Array.isArray(payload.risks) && payload.risks.length ? payload.risks : INITIAL_RISKS,
        );

        setAutomations(
          Array.isArray(payload.automations) && payload.automations.length
            ? payload.automations
            : INITIAL_AUTOMATIONS,
        );
      } catch (error) {
        console.warn('Projects overview fallback data used:', error?.message);
        setKpis(INITIAL_KPIS);
        setDeliveryTrend(INITIAL_DELIVERY_TREND);
        setResourceHeatmap(INITIAL_RESOURCE_HEATMAP);
        setBoard(JSON.parse(JSON.stringify(INITIAL_PROJECT_BOARD)));
        setMilestones(INITIAL_MILESTONES);
        setRisks(INITIAL_RISKS);
        setAutomations(INITIAL_AUTOMATIONS);
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, [currentCompany?.id]);

  const deliveryConfig = useMemo(() => {
    const data = Array.isArray(deliveryTrend)
      ? deliveryTrend.map((item) => ({
          ...item,
          value: Number(item?.value) || 0,
        }))
      : [];

    return {
      data,
      xField: 'month',
      yField: 'value',
      seriesField: 'type',
      smooth: true,
      color: ({ type }) => (type === 'Planned' ? '#1890ff' : '#52c41a'),
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${datum.value} story points`,
        }),
      },
    };
  }, [deliveryTrend]);

  const resourceConfig = useMemo(() => {
    const data = (Array.isArray(resourceHeatmap) ? resourceHeatmap : []).map((entry) => ({
      ...entry,
      load: Number(entry?.load) || 0,
    }));

    return {
      data,
      xField: 'squad',
      yField: 'load',
      columnStyle: { radius: [8, 8, 0, 0] },
      color: '#fa8c16',
      tooltip: {
        formatter: (datum) => ({
          name: datum.squad,
          value: `${datum.load}% capacity`,
        }),
      },
    };
  }, [resourceHeatmap]);

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

    setBoard((prev) => {
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
            [startColumn.id]: { ...startColumn, itemIds: newItemIds },
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
          [startColumn.id]: { ...startColumn, itemIds: startItemIds },
          [finishColumn.id]: { ...finishColumn, itemIds: finishItemIds },
        },
      };
    });
  };

  return (
    <div>
      <Title level={2}>
        Projects & Delivery Command Center{' '}
        {currentCompany?.name ? <Text type="secondary">· {currentCompany.name}</Text> : null}
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 780 }}>
        Align execution with strategy. Track progress, manage risks, and allocate squads with a
        visual project portfolio that ties budget burn, velocity, and milestones together.
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
                  precision={item.key === 'on_track' ? 1 : 0}
                  valueStyle={{ fontSize: 24 }}
                />
                <Space size={4}>
                  <ProjectOutlined style={{ color: item.trend >= 0 ? '#52c41a' : '#f5222d' }} />
                  <Text type={item.trend >= 0 ? 'success' : 'danger'}>
                    {item.trend > 0 ? '+' : ''}
                    {item.trend}%
                  </Text>
                  <Text type="secondary">vs last sprint</Text>
                </Space>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card
            title="Delivery Velocity"
            loading={loading}
            extra={
              <Space>
                <Button size="small" icon={<RocketOutlined />}>
                  Sync Sprint Metrics
                </Button>
                <Button size="small" icon={<ThunderboltOutlined />} type="primary">
                  Run Health Check
                </Button>
              </Space>
            }
          >
            <Area {...deliveryConfig} height={320} />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                Squad Load
              </Space>
            }
            loading={loading}
          >
            <Column {...resourceConfig} height={240} />
          </Card>
          <Card title="Top Risks" style={{ marginTop: 16 }} loading={loading}>
            <List
              dataSource={risks}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space>
                    <AlertOutlined style={{ color: severityColors[item.severity] || '#fa8c16' }} />
                    <Text>{item.title}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Project Portfolio Board"
        style={{ marginTop: 16 }}
        extra={<Text type="secondary">Drag projects across lifecycle stages to update portfolio</Text>}
      >
        <DragDropContext onDragEnd={handleDragEnd}>
          <Row gutter={[16, 16]}>
            {Object.values(board.columns).map((column) => (
              <Col xs={24} md={12} xl={6} key={column.id}>
                <Card
                  title={
                    <Space>
                      <DeploymentUnitOutlined />
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
                          const card = board.items[itemId];
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
                                      <Text strong>{card.name}</Text>
                                      <Tag color="purple">{card.owner}</Tag>
                                    </Space>
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
        <Col xs={24} md={12}>
          <Card title="Milestones" extra={<Button icon={<CalendarOutlined />}>Open Roadmap</Button>} loading={loading}>
            <Timeline
              items={milestones.map((item) => ({
                color: '#1890ff',
                children: (
                  <Space direction="vertical" size={0}>
                    <Text strong>{item.project}</Text>
                    <Text type="secondary">{item.date}</Text>
                    <Text type="secondary">{item.detail}</Text>
                  </Space>
                ),
              }))}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card
            title="Automation Recipes"
            extra={<Button icon={<ThunderboltOutlined />}>Create Automation</Button>}
            loading={loading}
          >
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
        </Col>
      </Row>
    </div>
  );
};

export default ProjectsWorkspace;
