import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Button,
  Space,
  List,
  Typography,
  Tabs,
  Tag,
  Timeline,
  Steps,
} from 'antd';
import {
  PlusOutlined,
  ThunderboltOutlined,
  PhoneOutlined,
  StarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RocketOutlined,
  GatewayOutlined,
} from '@ant-design/icons';
import { Column, Area } from '@ant-design/charts';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useCompany } from '../../contexts/CompanyContext';
import api from '../../services/api';

const { Title, Paragraph, Text } = Typography;

const INITIAL_KPIS = [
  {
    key: 'pipeline_value',
    label: 'Pipeline Value',
    value: 18500000,
    suffix: 'BDT',
    trend: 8,
  },
  {
    key: 'win_rate',
    label: 'Win Rate',
    value: 31.5,
    suffix: '%',
    trend: 3,
  },
  {
    key: 'avg_cycle',
    label: 'Avg Deal Cycle',
    value: 24,
    suffix: 'days',
    trend: -5,
  },
  {
    key: 'forecast_accuracy',
    label: 'Forecast Accuracy',
    value: 92,
    suffix: '%',
    trend: 4,
  },
];

const INITIAL_PIPELINE_BREAKDOWN = [
  { stage: 'Prospecting', value: 3600000 },
  { stage: 'Qualification', value: 4200000 },
  { stage: 'Proposal', value: 5200000 },
  { stage: 'Negotiation', value: 2800000 },
  { stage: 'Committed', value: 2700000 },
];

const INITIAL_REVENUE_FORECAST = [
  { month: 'Jun', committed: 4.2, upside: 1.5 },
  { month: 'Jul', committed: 4.6, upside: 1.8 },
  { month: 'Aug', committed: 4.9, upside: 2.1 },
  { month: 'Sep', committed: 5.2, upside: 2.4 },
  { month: 'Oct', committed: 5.4, upside: 2.6 },
];

const INITIAL_BOARD = {
  columns: {
    'col-prospecting': {
      id: 'col-prospecting',
      title: 'Prospecting',
      description: 'Fresh leads to qualify',
      itemIds: ['deal-101', 'deal-102'],
    },
    'col-qualification': {
      id: 'col-qualification',
      title: 'Qualification',
      description: 'Discovery underway',
      itemIds: ['deal-103', 'deal-104'],
    },
    'col-proposal': {
      id: 'col-proposal',
      title: 'Proposal',
      description: 'Pricing and solution alignment',
      itemIds: ['deal-105'],
    },
    'col-negotiation': {
      id: 'col-negotiation',
      title: 'Negotiation',
      description: 'Commercials in review',
      itemIds: ['deal-106'],
    },
  },
  items: {
    'deal-101': {
      id: 'deal-101',
      account: 'Acme Textiles',
      owner: 'Rahim Uddin',
      value: 850000,
      nextStep: 'Intro call Monday',
    },
    'deal-102': {
      id: 'deal-102',
      account: 'Northwind Apparel',
      owner: 'Sara Karim',
      value: 620000,
      nextStep: 'Share capability deck',
    },
    'deal-103': {
      id: 'deal-103',
      account: 'Dakota Fashion',
      owner: 'Lamia Hasan',
      value: 1150000,
      nextStep: 'Technical workshop',
    },
    'deal-104': {
      id: 'deal-104',
      account: 'Pixel Export',
      owner: 'Sajid Khan',
      value: 920000,
      nextStep: 'Budget confirmation',
    },
    'deal-105': {
      id: 'deal-105',
      account: 'Aurora Retail',
      owner: 'Rahim Uddin',
      value: 1380000,
      nextStep: 'Commercial proposal sent',
    },
    'deal-106': {
      id: 'deal-106',
      account: 'Silverline Foods',
      owner: 'Sara Karim',
      value: 1780000,
      nextStep: 'Legal redlines review',
    },
  },
};

const INITIAL_ACTIVITIES = [
  {
    id: 'activity-1',
    title: 'Follow-up call with Acme Textiles',
    owner: 'Rahim Uddin',
    due: 'Today · 3 PM',
  },
  {
    id: 'activity-2',
    title: 'Demo playback for Dakota Fashion',
    owner: 'Lamia Hasan',
    due: 'Tomorrow · 11 AM',
  },
  {
    id: 'activity-3',
    title: 'Negotiation round with Silverline Foods',
    owner: 'Sara Karim',
    due: 'In 2 days',
  },
];

const INITIAL_HIGHLIGHTS = [
  {
    id: 'highlight-1',
    account: 'Orion Home',
    detail: 'Upsell opportunity in pipeline · +420k BDT',
  },
  {
    id: 'highlight-2',
    account: 'Lotus Garments',
    detail: 'Stalled for 10 days · Needs executive touchpoint',
  },
  {
    id: 'highlight-3',
    account: 'Velocity Sports',
    detail: 'AI suggests discount optimisation',
  },
];

const INITIAL_ORDER_TO_CASH_FLOW = [
  {
    key: 'so',
    title: 'Sales Order',
    description: 'SO confirmed and stock reserved',
    status: 'finish',
    reference: 'SO-2025-0194',
  },
  {
    key: 'shipment',
    title: 'Shipment',
    description: 'Goods picked and dispatched',
    status: 'finish',
    reference: 'SHP-0442',
  },
  {
    key: 'event',
    title: 'stock.shipped event',
    description: 'Finance posted COGS via JournalEntryService',
    status: 'finish',
    reference: 'Event #4685',
  },
  {
    key: 'invoice',
    title: 'Sales Invoice',
    description: 'Accounts Receivable created',
    status: 'process',
    reference: 'INV-2025-0112',
  },
  {
    key: 'collection',
    title: 'Collection',
    description: 'Awaiting customer payment',
    status: 'wait',
    reference: '',
  },
];

const INITIAL_ORDER_TO_CASH_EVENTS = [
  {
    id: 'otc-event-1',
    label: 'SO confirmed',
    module: 'Sales',
    status: 'synced',
    timestamp: '2025-10-25 17:05',
    detail: 'SO-2025-0194 moved to Committed',
  },
  {
    id: 'otc-event-2',
    label: 'stock.shipped',
    module: 'Inventory',
    status: 'synced',
    timestamp: '2025-10-25 20:41',
    detail: 'Shipment SHP-0442 decreased StockLedger',
  },
  {
    id: 'otc-event-3',
    label: 'journal.posted',
    module: 'Finance',
    status: 'synced',
    timestamp: '2025-10-25 20:42',
    detail: 'Dr COGS -> Cr Inventory booked',
  },
  {
    id: 'otc-event-4',
    label: 'invoice.sent',
    module: 'Finance',
    status: 'pending',
    timestamp: '2025-10-25 21:10',
    detail: 'Invoice INV-2025-0112 emailed to customer',
  },
];

const otcEventStatusColors = {
  synced: 'green',
  pending: 'blue',
  failed: 'red',
};

const SalesWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState(INITIAL_KPIS);
  const [pipelineBreakdown, setPipelineBreakdown] = useState(INITIAL_PIPELINE_BREAKDOWN);
  const [forecastData, setForecastData] = useState(INITIAL_REVENUE_FORECAST);
  const [pipelineBoard, setPipelineBoard] = useState(INITIAL_BOARD);
  const [activities, setActivities] = useState(INITIAL_ACTIVITIES);
  const [highlights, setHighlights] = useState(INITIAL_HIGHLIGHTS);
  const [orderToCashFlow, setOrderToCashFlow] = useState(INITIAL_ORDER_TO_CASH_FLOW);
  const [orderToCashEvents, setOrderToCashEvents] = useState(INITIAL_ORDER_TO_CASH_EVENTS);

  useEffect(() => {
    const loadWorkspace = async () => {
      setLoading(true);
      try {
        if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
          setKpis(INITIAL_KPIS);
          setPipelineBreakdown(INITIAL_PIPELINE_BREAKDOWN);
          setForecastData(INITIAL_REVENUE_FORECAST);
          setPipelineBoard(JSON.parse(JSON.stringify(INITIAL_BOARD)));
          setActivities(INITIAL_ACTIVITIES);
          setHighlights(INITIAL_HIGHLIGHTS);
          return;
        }

        const response = await api.get('/api/v1/sales/overview/', {
          params: { company: currentCompany?.id },
        });
        const payload = response.data || {};

        setKpis(Array.isArray(payload.kpis) && payload.kpis.length ? payload.kpis : INITIAL_KPIS);
        setPipelineBreakdown(
          Array.isArray(payload.pipeline_breakdown) && payload.pipeline_breakdown.length
            ? payload.pipeline_breakdown
            : INITIAL_PIPELINE_BREAKDOWN,
        );
        setForecastData(
          Array.isArray(payload.forecast) && payload.forecast.length
            ? payload.forecast
            : INITIAL_REVENUE_FORECAST,
        );
        if (
          payload.pipeline_board &&
          payload.pipeline_board.columns &&
          payload.pipeline_board.items
        ) {
          setPipelineBoard(payload.pipeline_board);
        } else {
          setPipelineBoard(JSON.parse(JSON.stringify(INITIAL_BOARD)));
        }
        setActivities(
          Array.isArray(payload.next_actions) && payload.next_actions.length
            ? payload.next_actions
            : INITIAL_ACTIVITIES,
        );
        setHighlights(
          Array.isArray(payload.highlights) && payload.highlights.length
            ? payload.highlights
            : INITIAL_HIGHLIGHTS,
        );

        if (Array.isArray(payload.order_to_cash?.steps) && payload.order_to_cash.steps.length) {
          setOrderToCashFlow(
            payload.order_to_cash.steps.map((step, index) => ({
              key: step.key || step.id || `otc-step-${index}`,
              title:
                step.title ||
                step.name ||
                INITIAL_ORDER_TO_CASH_FLOW[index % INITIAL_ORDER_TO_CASH_FLOW.length].title,
              description:
                step.description ||
                INITIAL_ORDER_TO_CASH_FLOW[index % INITIAL_ORDER_TO_CASH_FLOW.length].description,
              status:
                step.status ||
                INITIAL_ORDER_TO_CASH_FLOW[index % INITIAL_ORDER_TO_CASH_FLOW.length].status,
              reference: step.reference || step.reference_code || '',
            })),
          );
        } else {
          setOrderToCashFlow(INITIAL_ORDER_TO_CASH_FLOW);
        }

        if (Array.isArray(payload.order_to_cash?.events) && payload.order_to_cash.events.length) {
          setOrderToCashEvents(
            payload.order_to_cash.events.map((event, index) => ({
              id: event.id || `otc-event-${index}`,
              label: event.label || event.event || 'order_to_cash.event',
              module: event.module || event.source || 'sales',
              status: event.status || 'synced',
              timestamp: event.timestamp || event.created_at || '',
              detail:
                event.detail ||
                event.description ||
                INITIAL_ORDER_TO_CASH_EVENTS[index % INITIAL_ORDER_TO_CASH_EVENTS.length].detail,
            })),
          );
        } else {
          setOrderToCashEvents(INITIAL_ORDER_TO_CASH_EVENTS);
        }
      } catch (error) {
        console.warn('Sales overview fallback data used:', error?.message);
        setKpis(INITIAL_KPIS);
        setPipelineBreakdown(INITIAL_PIPELINE_BREAKDOWN);
        setForecastData(INITIAL_REVENUE_FORECAST);
        setPipelineBoard(JSON.parse(JSON.stringify(INITIAL_BOARD)));
        setActivities(INITIAL_ACTIVITIES);
        setHighlights(INITIAL_HIGHLIGHTS);
        setOrderToCashFlow(INITIAL_ORDER_TO_CASH_FLOW);
        setOrderToCashEvents(INITIAL_ORDER_TO_CASH_EVENTS);
      } finally {
        setLoading(false);
      }
    };

    loadWorkspace();
  }, [currentCompany]);

  const pipelineConfig = useMemo(() => {
    const safeData = (Array.isArray(pipelineBreakdown) ? pipelineBreakdown : []).map((item) => ({
      ...item,
      value: Number(item?.value) || 0,
    }));
    return {
      data: safeData,
      xField: 'stage',
      yField: 'value',
      columnStyle: { radius: [8, 8, 0, 0] },
      color: '#5b8ff9',
      tooltip: {
        formatter: (datum) => ({
          name: datum.stage,
          value: `৳ ${(Number(datum.value) || 0).toLocaleString()}`,
        }),
      },
    };
  }, [pipelineBreakdown]);

  const forecastConfig = useMemo(() => {
    const safeData = (Array.isArray(forecastData) ? forecastData : []).reduce((acc, item) => {
      acc.push({ month: item.month, type: 'Committed', value: Number(item?.committed) || 0 });
      acc.push({ month: item.month, type: 'Upside', value: Number(item?.upside) || 0 });
      return acc;
    }, []);
    return {
      data: safeData,
      xField: 'month',
      yField: 'value',
      seriesField: 'type',
      smooth: true,
      color: ({ type }) => (type === 'Committed' ? '#52c41a' : '#faad14'),
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${Number(datum.value).toFixed(1)}M BDT`,
        }),
      },
    };
  }, [forecastData]);

  const orderToCashSteps = useMemo(
    () =>
      (Array.isArray(orderToCashFlow) ? orderToCashFlow : INITIAL_ORDER_TO_CASH_FLOW).map((step) => ({
        ...step,
        status: step.status || 'wait',
      })),
    [orderToCashFlow],
  );

  const activeOtcStepIndex = useMemo(() => {
    if (!Array.isArray(orderToCashSteps)) {
      return 0;
    }
    const processIndex = orderToCashSteps.findIndex((step) => step.status === 'process');
    if (processIndex >= 0) {
      return processIndex;
    }
    const finishIndex = orderToCashSteps.reduce(
      (acc, step, idx) => (step.status === 'finish' ? idx : acc),
      -1,
    );
    return finishIndex >= 0 ? finishIndex : 0;
  }, [orderToCashSteps]);

  const recentOtcEvents = useMemo(
    () => (Array.isArray(orderToCashEvents) ? orderToCashEvents.slice(0, 5) : []),
    [orderToCashEvents],
  );

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

    setPipelineBoard((prev) => {
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
      const newStartColumn = { ...startColumn, itemIds: startItemIds };

      const finishItemIds = Array.from(finishColumn.itemIds);
      finishItemIds.splice(destination.index, 0, draggableId);
      const newFinishColumn = { ...finishColumn, itemIds: finishItemIds };

      return {
        ...prev,
        columns: {
          ...prev.columns,
          [newStartColumn.id]: newStartColumn,
          [newFinishColumn.id]: newFinishColumn,
        },
      };
    });
  };

  return (
    <div>
      <Title level={2}>
        Sales & CRM Control Tower{' '}
        {currentCompany?.name ? <Text type="secondary">· {currentCompany.name}</Text> : null}
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 780 }}>
        Monitor pipeline velocity, forecast accuracy, and next-best actions across the revenue
        lifecycle. Drag-and-drop deals, trigger playbooks, and keep the sales engine aligned with
        Twist ERP.
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
                  precision={item.key === 'win_rate' || item.key === 'forecast_accuracy' ? 1 : 0}
                  valueStyle={{ fontSize: 24 }}
                />
                <Space size={4}>
                  {item.trend >= 0 ? (
                    <ArrowUpOutlined style={{ color: '#52c41a' }} />
                  ) : (
                    <ArrowDownOutlined style={{ color: '#f5222d' }} />
                  )}
                  <Text type={item.trend >= 0 ? 'success' : 'danger'}>
                    {Math.abs(item.trend)}%
                  </Text>
                  <Text type="secondary">vs last quarter</Text>
                </Space>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={16}>
          <Card title="Order-to-Cash Flow" loading={loading}>
            <Steps
              current={activeOtcStepIndex}
              items={orderToCashSteps.map((step) => ({
                title: step.title,
                description: step.description,
                status: step.status,
              }))}
            />
            <List
              style={{ marginTop: 16 }}
              dataSource={orderToCashSteps}
              renderItem={(step) => (
                <List.Item key={step.key}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <Tag color={step.status === 'finish' ? 'green' : step.status === 'process' ? 'blue' : 'default'}>
                        {step.status.toUpperCase()}
                      </Tag>
                      <Text strong>{step.title}</Text>
                      {step.reference ? <Text type="secondary">Ref: {step.reference}</Text> : null}
                    </Space>
                    <Text type="secondary">{step.description}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Revenue Events Bridge" loading={loading}>
            <List
              size="small"
              dataSource={recentOtcEvents}
              renderItem={(event) => (
                <List.Item key={event.id}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <GatewayOutlined style={{ color: '#722ed1' }} />
                      <Text strong>{event.label}</Text>
                      <Tag color={otcEventStatusColors[event.status] || 'blue'}>
                        {(event.status || 'synced').toUpperCase()}
                      </Tag>
                    </Space>
                    <Text type="secondary">{event.detail}</Text>
                    <Text type="secondary">
                      Module: {event.module} | {event.timestamp}
                    </Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card
            title="Pipeline by Stage"
            loading={loading}
            extra={
              <Space>
                <Button icon={<ThunderboltOutlined />}>AI Pipeline Boost</Button>
                <Button type="primary" icon={<PlusOutlined />}>
                  New Opportunity
                </Button>
              </Space>
            }
          >
            <Column {...pipelineConfig} height={320} />
          </Card>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} md={12}>
              <Card title="Forecast Outlook" loading={loading}>
                <Area {...forecastConfig} height={240} />
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="Action Queue" loading={loading}>
                <List
                  dataSource={activities}
                  renderItem={(item) => (
                    <List.Item key={item.id}>
                      <Space direction="vertical" size={0}>
                        <Space>
                          <PhoneOutlined style={{ color: '#1890ff' }} />
                          <Text strong>{item.title}</Text>
                        </Space>
                        <Text type="secondary">
                          Owner: {item.owner} · {item.due}
                        </Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>

          <Card
            title="Pipeline Board"
            style={{ marginTop: 16 }}
            extra={<Text type="secondary">Drag deals across stages to update status</Text>}
          >
            <DragDropContext onDragEnd={handleDragEnd}>
              <Row gutter={[16, 16]}>
                {Object.values(pipelineBoard.columns).map((column) => (
                  <Col xs={24} lg={6} key={column.id}>
                    <Card
                      title={
                        <Space>
                          {column.title}
                          <Tag>{column.itemIds.length}</Tag>
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
                              background: snapshot.isDraggingOver ? '#e6f7ff' : 'transparent',
                              borderRadius: 8,
                              padding: 4,
                              transition: 'background-color 0.2s ease',
                            }}
                          >
                            {column.itemIds.map((itemId, index) => {
                              const item = pipelineBoard.items[itemId];
                              if (!item) {
                                return null;
                              }
                              return (
                                <Draggable draggableId={item.id} index={index} key={item.id}>
                                  {(dragProvided, dragSnapshot) => (
                                    <Card
                                      size="small"
                                      ref={dragProvided.innerRef}
                                      {...dragProvided.draggableProps}
                                      {...dragProvided.dragHandleProps}
                                      style={{
                                        marginBottom: 8,
                                        boxShadow: dragSnapshot.isDragging
                                          ? '0 8px 16px rgba(24, 144, 255, 0.25)'
                                          : '0 1px 3px rgba(0,0,0,0.08)',
                                        border: '1px solid #f0f0f0',
                                      }}
                                    >
                                      <Space direction="vertical" size={0} style={{ width: '100%' }}>
                                        <Space
                                          align="baseline"
                                          style={{ justifyContent: 'space-between', width: '100%' }}
                                        >
                                          <Text strong>{item.account}</Text>
                                          <Tag color="blue">
                                            ৳ {(item.value || 0).toLocaleString()}
                                          </Tag>
                                        </Space>
                                        <Space
                                          align="baseline"
                                          style={{ justifyContent: 'space-between', width: '100%' }}
                                        >
                                          <Text type="secondary">{item.owner}</Text>
                                          <Text type="secondary">{item.nextStep}</Text>
                                        </Space>
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
        </Col>

        <Col xs={24} xl={8}>
          <Card title="Highlights" style={{ marginBottom: 16 }} loading={loading}>
            <List
              dataSource={highlights}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Space>
                      <StarOutlined style={{ color: '#faad14' }} />
                      <Text strong>{item.account}</Text>
                    </Space>
                    <Text type="secondary">{item.detail}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Tabs
            defaultActiveKey="calls"
            items={[
              {
                key: 'calls',
                label: 'Call Blitz',
                children: (
                  <List
                    dataSource={[
                      { id: 'call-1', title: 'Call Orion Home', detail: 'Post-demo check-in' },
                      { id: 'call-2', title: 'Call Velocity Sports', detail: 'Negotiate pricing' },
                      { id: 'call-3', title: 'Call Lotus Garments', detail: 'Confirm trial setup' },
                    ]}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space>
                          <PhoneOutlined style={{ color: '#1890ff' }} />
                          <Space direction="vertical" size={0}>
                            <Text strong>{item.title}</Text>
                            <Text type="secondary">{item.detail}</Text>
                          </Space>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
              {
                key: 'playbooks',
                label: 'Playbooks',
                children: (
                  <List
                    dataSource={[
                      {
                        id: 'play-1',
                        title: 'Revive stalled deals',
                        detail: 'Trigger nurture sequence · AI summary included',
                      },
                      {
                        id: 'play-2',
                        title: 'Accelerate negotiations',
                        detail: 'Recommend bundle discount for high LTV accounts',
                      },
                      {
                        id: 'play-3',
                        title: 'Reference program',
                        detail: 'Flag best-fit champions for upcoming case study',
                      },
                    ]}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space>
                          <RocketOutlined style={{ color: '#52c41a' }} />
                          <Space direction="vertical" size={0}>
                            <Text strong>{item.title}</Text>
                            <Text type="secondary">{item.detail}</Text>
                          </Space>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
          />

          <Card title="Revenue Timeline" style={{ marginTop: 16 }}>
            <Timeline
              items={[
                {
                  color: 'blue',
                  children: (
                    <>
                      <Text strong>Today · Forecast snapshot</Text>
                      <br />
                      <Text type="secondary">AI recalculated probabilities based on latest signals</Text>
                    </>
                  ),
                },
                {
                  color: 'green',
                  children: (
                    <>
                      <Text strong>Tomorrow · Executive review</Text>
                      <br />
                      <Text type="secondary">Focus on deals &gt; ৳1M with close date this month</Text>
                    </>
                  ),
                },
                {
                  color: 'orange',
                  children: (
                    <>
                      <Text strong>Next Week · Playbook launch</Text>
                      <br />
                      <Text type="secondary">Automate follow-up for dormant leads &gt; 14 days</Text>
                    </>
                  ),
                },
                {
                  color: 'red',
                  children: (
                    <>
                      <Text strong>Quarter End · Board pack</Text>
                      <br />
                      <Text type="secondary">Forecast accuracy review with finance</Text>
                    </>
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

export default SalesWorkspace;
