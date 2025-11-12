import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  FileProtectOutlined,
  SafetyCertificateOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ShoppingCartOutlined,
  GatewayOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { Column, Area } from '@ant-design/charts';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useCompany } from '../../contexts/CompanyContext';
import api from '../../services/api';

const { Title, Paragraph, Text } = Typography;

const INITIAL_KPIS = [
  {
    key: 'spend',
    label: 'Spend Month-to-Date',
    value: 9400000,
    suffix: 'BDT',
    trend: -6,
  },
  {
    key: 'savings',
    label: 'Savings Realised',
    value: 720000,
    suffix: 'BDT',
    trend: 12,
  },
  {
    key: 'on_time',
    label: 'On-time Deliveries',
    value: 93,
    suffix: '%',
    trend: 5,
  },
  {
    key: 'compliance',
    label: 'Policy Compliance',
    value: 96,
    suffix: '%',
    trend: 3,
  },
];

const INITIAL_CATEGORY_SPEND = [
  { category: 'Raw Material', value: 4.8 },
  { category: 'Chemicals', value: 2.1 },
  { category: 'Packaging', value: 1.6 },
  { category: 'Logistics', value: 1.1 },
  { category: 'Services', value: 0.9 },
];

const INITIAL_SUPPLIER_PERFORMANCE = [
  { month: 'Jan', on_time: 88, quality: 94 },
  { month: 'Feb', on_time: 90, quality: 95 },
  { month: 'Mar', on_time: 92, quality: 96 },
  { month: 'Apr', on_time: 91, quality: 94 },
  { month: 'May', on_time: 93, quality: 97 },
  { month: 'Jun', on_time: 95, quality: 98 },
];

const INITIAL_APPROVAL_BOARD = {
  columns: {
    'stage-intake': {
      id: 'stage-intake',
      title: 'Intake',
      description: 'New requisitions',
      itemIds: ['req-101', 'req-102'],
    },
    'stage-evaluating': {
      id: 'stage-evaluating',
      title: 'Evaluating',
      description: 'RFQs & vendor analysis',
      itemIds: ['req-103', 'req-104'],
    },
    'stage-approval': {
      id: 'stage-approval',
      title: 'Awaiting Approval',
      description: 'Budget & compliance review',
      itemIds: ['req-105'],
    },
    'stage-ordered': {
      id: 'stage-ordered',
      title: 'Ordered',
      description: 'PO released & tracking',
      itemIds: ['req-106'],
    },
  },
  items: {
    'req-101': {
      id: 'req-101',
      title: 'Reactive Dye Navy Blue',
      requester: 'Print Unit',
      value: 320000,
      nextStep: 'Collect quotes',
    },
    'req-102': {
      id: 'req-102',
      title: 'Elastic Band 25mm',
      requester: 'Accessory Store',
      value: 180000,
      nextStep: 'Validate specifications',
    },
    'req-103': {
      id: 'req-103',
      title: 'Carton Boxes (Export)',
      requester: 'Logistics',
      value: 240000,
      nextStep: 'Compare supplier bids',
    },
    'req-104': {
      id: 'req-104',
      title: 'Cold Storage Maintenance',
      requester: 'Facilities',
      value: 95000,
      nextStep: 'Review service SLA',
    },
    'req-105': {
      id: 'req-105',
      title: 'Knitted Fabric Lot #123',
      requester: 'Production',
      value: 780000,
      nextStep: 'COO approval',
    },
    'req-106': {
      id: 'req-106',
      title: 'Thread Cones (multiple colors)',
      requester: 'Stitching Unit',
      value: 165000,
      nextStep: 'Monitor delivery ETA',
    },
  },
};

const INITIAL_SUPPLIER_ALERTS = [
  {
    id: 'alert-1',
    supplier: 'Dhaka Cotton Mills',
    detail: 'Late delivery · PO-2031 delayed by 3 days',
    severity: 'warning',
  },
  {
    id: 'alert-2',
    supplier: 'ColorSync Ltd.',
    detail: 'Quality deviation flagged in latest batch',
    severity: 'critical',
  },
  {
    id: 'alert-3',
    supplier: 'Rapid Box Solutions',
    detail: 'Contract renewal due in 10 days',
    severity: 'info',
  },
];

const INITIAL_TASKS = [
  {
    id: 'task-1',
    title: 'Review RFQ responses for packaging RFP',
    owner: 'Procurement Squad',
    due: 'Today · 4 PM',
  },
  {
    id: 'task-2',
    title: 'Compliance audit for supplier onboarding',
    owner: 'Compliance Team',
    due: 'Tomorrow · 2 PM',
  },
  {
    id: 'task-3',
    title: 'Negotiate payment terms with ColorSync',
    owner: 'Category Manager',
    due: 'In 3 days',
  },
];

const INITIAL_PROCURE_TO_PAY_FLOW = [
  {
    key: 'po',
    title: 'Purchase Order',
    description: 'PO released from Procurement',
    status: 'finish',
    reference: 'PO-2025-0041',
  },
  {
    key: 'grn',
    title: 'Goods Receipt',
    description: 'Inventory increased in Stock Ledger',
    status: 'finish',
    reference: 'GRN-0778',
  },
  {
    key: 'event',
    title: 'stock.received event',
    description: 'Finance auto-posted Inventory -> GRNI',
    status: 'finish',
    reference: 'Event #4583',
  },
  {
    key: 'invoice',
    title: 'Supplier Invoice',
    description: 'Accounts Payable pending approval',
    status: 'process',
    reference: 'BILL-0091',
  },
  {
    key: 'payment',
    title: 'Payment',
    description: 'Awaiting payment run',
    status: 'wait',
    reference: '',
  },
];

const INITIAL_PROCURE_TO_PAY_EVENTS = [
  {
    id: 'p2p-event-1',
    label: 'PO created',
    module: 'Procurement',
    status: 'synced',
    timestamp: '2025-10-25 18:12',
    detail: 'PO-2025-0041 approved and dispatched',
  },
  {
    id: 'p2p-event-2',
    label: 'stock.received',
    module: 'Inventory',
    status: 'synced',
    timestamp: '2025-10-25 21:18',
    detail: 'GRN-0778 posted, StockLedgerEntry created',
  },
  {
    id: 'p2p-event-3',
    label: 'journal.posted',
    module: 'Finance',
    status: 'synced',
    timestamp: '2025-10-25 21:19',
    detail: 'Dr Inventory -> Cr GRNI via JournalEntryService',
  },
  {
    id: 'p2p-event-4',
    label: 'invoice.created',
    module: 'Finance',
    status: 'pending',
    timestamp: '2025-10-25 21:45',
    detail: 'Supplier invoice waiting validation',
  },
];

const flowStatusColors = {
  finish: 'green',
  process: 'blue',
  wait: 'default',
};

const eventStatusColors = {
  synced: 'green',
  pending: 'blue',
  failed: 'red',
};

const ProcurementWorkspace = () => {
  const { currentCompany } = useCompany();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState(INITIAL_KPIS);
  const [categorySpend, setCategorySpend] = useState(INITIAL_CATEGORY_SPEND);
  const [supplierPerformance, setSupplierPerformance] = useState(INITIAL_SUPPLIER_PERFORMANCE);
  const [approvalBoard, setApprovalBoard] = useState(INITIAL_APPROVAL_BOARD);
  const [supplierAlerts, setSupplierAlerts] = useState(INITIAL_SUPPLIER_ALERTS);
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const [p2pFlow, setP2pFlow] = useState(INITIAL_PROCURE_TO_PAY_FLOW);
  const [p2pEvents, setP2pEvents] = useState(INITIAL_PROCURE_TO_PAY_EVENTS);

  useEffect(() => {
    const loadWorkspace = async () => {
      setLoading(true);
      try {
        if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
          setKpis(INITIAL_KPIS);
          setCategorySpend(INITIAL_CATEGORY_SPEND);
          setSupplierPerformance(INITIAL_SUPPLIER_PERFORMANCE);
          setApprovalBoard(JSON.parse(JSON.stringify(INITIAL_APPROVAL_BOARD)));
          setSupplierAlerts(INITIAL_SUPPLIER_ALERTS);
          setTasks(INITIAL_TASKS);
          setP2pFlow(INITIAL_PROCURE_TO_PAY_FLOW);
          setP2pEvents(INITIAL_PROCURE_TO_PAY_EVENTS);
          return;
        }

        const response = await api.get('/api/v1/procurement/overview/', {
          params: { company: currentCompany?.id },
        });
        const payload = response.data || {};

        setKpis(Array.isArray(payload.kpis) && payload.kpis.length ? payload.kpis : INITIAL_KPIS);
        setCategorySpend(
          Array.isArray(payload.category_spend) && payload.category_spend.length
            ? payload.category_spend
            : INITIAL_CATEGORY_SPEND,
        );
        setSupplierPerformance(
          Array.isArray(payload.supplier_performance) && payload.supplier_performance.length
            ? payload.supplier_performance
            : INITIAL_SUPPLIER_PERFORMANCE,
        );
        if (
          payload.approval_board &&
          payload.approval_board.columns &&
          payload.approval_board.budget_items
        ) {
          setApprovalBoard(payload.approval_board);
        } else {
          setApprovalBoard(JSON.parse(JSON.stringify(INITIAL_APPROVAL_BOARD)));
        }
        setSupplierAlerts(
          Array.isArray(payload.alerts) && payload.alerts.length
            ? payload.alerts
            : INITIAL_SUPPLIER_ALERTS,
        );
        setTasks(
          Array.isArray(payload.tasks) && payload.tasks.length ? payload.tasks : INITIAL_TASKS,
        );

        if (Array.isArray(payload.procure_to_pay?.steps) && payload.procure_to_pay.steps.length) {
          setP2pFlow(
            payload.procure_to_pay.steps.map((step, index) => ({
              key: step.key || step.id || `p2p-step-${index}`,
              title:
                step.title ||
                step.name ||
                INITIAL_PROCURE_TO_PAY_FLOW[index % INITIAL_PROCURE_TO_PAY_FLOW.length].title,
              description:
                step.description ||
                INITIAL_PROCURE_TO_PAY_FLOW[index % INITIAL_PROCURE_TO_PAY_FLOW.length].description,
              status:
                step.status ||
                INITIAL_PROCURE_TO_PAY_FLOW[index % INITIAL_PROCURE_TO_PAY_FLOW.length].status,
              reference: step.reference || step.reference_code || '',
            })),
          );
        } else {
          setP2pFlow(INITIAL_PROCURE_TO_PAY_FLOW);
        }

        if (Array.isArray(payload.procure_to_pay?.events) && payload.procure_to_pay.events.length) {
          setP2pEvents(
            payload.procure_to_pay.events.map((event, index) => ({
              id: event.id || `p2p-event-${index}`,
              label: event.label || event.event || 'procure_to_pay.event',
              module: event.module || event.source || 'procurement',
              status: event.status || 'synced',
              timestamp: event.timestamp || event.created_at || '',
              detail:
                event.detail ||
                event.description ||
                INITIAL_PROCURE_TO_PAY_EVENTS[index % INITIAL_PROCURE_TO_PAY_EVENTS.length].detail,
            })),
          );
        } else {
          setP2pEvents(INITIAL_PROCURE_TO_PAY_EVENTS);
        }
      } catch (error) {
        console.warn('Procurement overview fallback data used:', error?.message);
        setKpis(INITIAL_KPIS);
        setCategorySpend(INITIAL_CATEGORY_SPEND);
        setSupplierPerformance(INITIAL_SUPPLIER_PERFORMANCE);
        setApprovalBoard(JSON.parse(JSON.stringify(INITIAL_APPROVAL_BOARD)));
        setSupplierAlerts(INITIAL_SUPPLIER_ALERTS);
        setTasks(INITIAL_TASKS);
        setP2pFlow(INITIAL_PROCURE_TO_PAY_FLOW);
        setP2pEvents(INITIAL_PROCURE_TO_PAY_EVENTS);
      } finally {
        setLoading(false);
      }
    };

    loadWorkspace();
  }, [currentCompany]);

  const spendConfig = useMemo(() => {
    const safeData = (Array.isArray(categorySpend) ? categorySpend : []).map((item) => ({
      ...budget_item,
      value: Number(item?.value) || 0,
    }));
    return {
      data: safeData,
      xField: 'category',
      yField: 'value',
      columnStyle: { radius: [8, 8, 0, 0] },
      color: '#5b8ff9',
      tooltip: {
        formatter: (datum) => ({
          name: datum.category,
          value: `${datum.value}M BDT`,
        }),
      },
    };
  }, [categorySpend]);

  const performanceConfig = useMemo(() => {
    const safeData = (Array.isArray(supplierPerformance) ? supplierPerformance : []).reduce(
      (acc, item) => {
        acc.push({ month: item.month, type: 'On-Time', value: Number(item?.on_time) || 0 });
        acc.push({ month: item.month, type: 'Quality', value: Number(item?.quality) || 0 });
        return acc;
      },
      [],
    );
    return {
      data: safeData,
      xField: 'month',
      yField: 'value',
      seriesField: 'type',
      smooth: true,
      color: ({ type }) => (type === 'On-Time' ? '#52c41a' : '#faad14'),
      yAxis: { max: 100 },
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${datum.value}%`,
        }),
      },
    };
  }, [supplierPerformance]);

  const procureToPaySteps = useMemo(
    () =>
      (Array.isArray(p2pFlow) ? p2pFlow : INITIAL_PROCURE_TO_PAY_FLOW).map((step) => ({
        ...step,
        status: step.status || 'wait',
      })),
    [p2pFlow],
  );

  const activeP2pStepIndex = useMemo(() => {
    if (!Array.isArray(procureToPaySteps)) {
      return 0;
    }
    const index = procureToPaySteps.findIndex((step) => step.status === 'process');
    if (index >= 0) {
      return index;
    }
    const finishIndex = procureToPaySteps.reduce(
      (acc, step, idx) => (step.status === 'finish' ? idx : acc),
      -1,
    );
    return finishIndex >= 0 ? finishIndex : 0;
  }, [procureToPaySteps]);

  const recentP2pEvents = useMemo(
    () => (Array.isArray(p2pEvents) ? p2pEvents.slice(0, 5) : []),
    [p2pEvents],
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

    setApprovalBoard((prev) => {
      const startColumn = prev.columns[source.droppableId];
      const finishColumn = prev.columns[destination.droppableId];
      if (!startColumn || !finishColumn) {
        return prev;
      }
      if (startColumn === finishColumn) {
        const newItemIds = Array.from(startColumn.budget_itemIds);
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
      const startItemIds = Array.from(startColumn.budget_itemIds);
      startItemIds.splice(source.index, 1);
      const newStartColumn = { ...startColumn, itemIds: startItemIds };

      const finishItemIds = Array.from(finishColumn.budget_itemIds);
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
        Procurement Control Tower{' '}
        {currentCompany?.name ? <Text type="secondary">· {currentCompany.name}</Text> : null}
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 780 }}>
        Orchestrate spend, approvals, and supplier risk with the Twist ERP procurement workspace.
        Monitor savings, automate compliance, and streamline sourcing decisions.
      </Paragraph>

      <Space style={{ marginBottom: 24 }} size="middle">
        <Button
          type="primary"
          size="large"
          icon={<InboxOutlined />}
          onClick={() => navigate('/inventory/goods-receipts')}
        >
          Create Goods Receipt (GRN)
        </Button>
        <Button
          icon={<PlusOutlined />}
          size="large"
          onClick={() => navigate('/procurement/orders')}
        >
          New Purchase Order
        </Button>
        <Button
          icon={<ShoppingCartOutlined />}
          size="large"
        >
          New Requisition
        </Button>
      </Space>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {kpis.map((item) => (
          <Col key={item.key} xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Space direction="vertical" size={4}>
                <Text type="secondary">{item.label}</Text>
                <Statistic
                  value={item.value}
                  suffix={item.suffix}
                  precision={item.key === 'savings' ? 0 : item.key.includes('%)') ? 1 : 0}
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
                  <Text type="secondary">vs last month</Text>
                </Space>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={16}>
          <Card title="Procure-to-Pay Flow" loading={loading}>
            <Steps
              current={activeP2pStepIndex}
              items={procureToPaySteps.map((step) => ({
                title: step.title,
                description: step.description,
                status: step.status,
              }))}
            />
            <List
              style={{ marginTop: 16 }}
              dataSource={procureToPaySteps}
              renderItem={(step) => (
                <List.Item key={step.key}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <Tag color={flowStatusColors[step.status] || 'default'}>
                        {step.status.toUpperCase()}
                      </Tag>
                      <Text strong>{step.title}</Text>
                      {step.reference ? (
                        <Text type="secondary">Ref: {step.reference}</Text>
                      ) : null}
                    </Space>
                    <Text type="secondary">{step.description}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Cross-Module Events" loading={loading}>
            <List
              size="small"
              dataSource={recentP2pEvents}
              renderItem={(event) => (
                <List.Item key={event.id}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <GatewayOutlined style={{ color: '#5b8ff9' }} />
                      <Text strong>{event.label}</Text>
                      <Tag color={eventStatusColors[event.status] || 'blue'}>
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
            title="Spend by Category"
            loading={loading}
            extra={
              <Space>
                <Button icon={<FileProtectOutlined />}>Spend Compliance</Button>
                <Button icon={<PlusOutlined />} type="primary">
                  New Requisition
                </Button>
              </Space>
            }
          >
            <Column {...spendConfig} height={320} />
          </Card>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} md={12}>
              <Card title="Supplier Performance" loading={loading}>
                <Area {...performanceConfig} height={240} />
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="Action Items" loading={loading}>
                <List
                  dataSource={tasks}
                  renderItem={(item) => (
                    <List.Item key={item.id}>
                      <Space direction="vertical" size={0}>
                        <Space>
                          <ThunderboltOutlined style={{ color: '#722ed1' }} />
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
            title="Approval Flow"
            style={{ marginTop: 16 }}
            extra={<Text type="secondary">Drag cards to progress requisitions</Text>}
          >
            <DragDropContext onDragEnd={handleDragEnd}>
              <Row gutter={[16, 16]}>
                {Object.values(approvalBoard.columns).map((column) => (
                  <Col xs={24} lg={6} key={column.id}>
                    <Card
                      title={
                        <Space direction="vertical" size={0}>
                          <Text strong>{column.title}</Text>
                          <Text type="secondary">{column.description}</Text>
                        </Space>
                      }
                      bodyStyle={{ padding: 12, minHeight: 260 }}
                    >
                      <Droppable droppableId={column.id}>
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.droppableProps}
                            style={{
                              minHeight: 220,
                              background: snapshot.isDraggingOver ? '#fff7e6' : 'transparent',
                              borderRadius: 8,
                              padding: 4,
                            }}
                          >
                            {column.budget_itemIds.map((itemId, index) => {
                              const request = approvalBoard.budget_items[itemId];
                              if (!request) {
                                return null;
                              }
                              return (
                                <Draggable draggableId={itemId} index={index} key={itemId}>
                                  {(dragProvided, dragSnapshot) => (
                                    <Card
                                      size="small"
                                      ref={dragProvided.innerRef}
                                      {...dragProvided.draggableProps}
                                      {...dragProvided.dragHandleProps}
                                      style={{
                                        marginBottom: 8,
                                        boxShadow: dragSnapshot.isDragging
                                          ? '0 8px 16px rgba(250, 173, 20, 0.25)'
                                          : '0 1px 3px rgba(0,0,0,0.08)',
                                        border: '1px solid #f0f0f0',
                                      }}
                                    >
                                      <Space direction="vertical" size={0} style={{ width: '100%' }}>
                                        <Text strong>{request.title}</Text>
                                        <Space
                                          align="baseline"
                                          style={{ justifyContent: 'space-between', width: '100%' }}
                                        >
                                          <Text type="secondary">{request.requester}</Text>
                                          <Tag color="blue">
                                            ৳ {(request.value || 0).toLocaleString()}
                                          </Tag>
                                        </Space>
                                        <Text type="secondary">{request.nextStep}</Text>
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
          <Card title="Supplier Alerts" style={{ marginBottom: 16 }} loading={loading}>
            <List
              dataSource={supplierAlerts}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Space>
                      <SafetyCertificateOutlined
                        style={{ color: item.severity === 'critical' ? '#f5222d' : '#faad14' }}
                      />
                      <Text strong>{item.supplier}</Text>
                    </Space>
                    <Text type="secondary">{item.detail}</Text>
                    <Tag color={item.severity === 'critical' ? 'red' : item.severity === 'warning' ? 'orange' : 'blue'}>
                      {item.severity.toUpperCase()}
                    </Tag>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Tabs
            defaultActiveKey="contracts"
            items={[
              {
                key: 'contracts',
                label: 'Contracts',
                children: (
                  <List
                    dataSource={[
                      { id: 'contract-1', title: 'Dhaka Cotton Mills', detail: 'Renewal in 45 days' },
                      { id: 'contract-2', title: 'ColorSync Ltd.', detail: 'Compliance review pending' },
                      { id: 'contract-3', title: 'Rapid Box Solutions', detail: 'Pricing benchmark queued' },
                    ]}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space>
                          <FileProtectOutlined style={{ color: '#1890ff' }} />
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
                key: 'catalog',
                label: 'Catalog Updates',
                children: (
                  <List
                    dataSource={[
                      { id: 'cat-1', title: 'Add eco-friendly packaging SKUs', detail: 'Awaiting approval' },
                      { id: 'cat-2', title: 'Deactivate obsolete dye lot', detail: 'QA sign-off required' },
                    ]}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space>
                          <ShoppingCartOutlined style={{ color: '#52c41a' }} />
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

          <Card title="Governance Timeline" style={{ marginTop: 16 }}>
            <Timeline
              items={[
                {
                  color: 'blue',
                  children: (
                    <>
                      <Text strong>Today · Spend review</Text>
                      <br />
                      <Text type="secondary">Finance alignment on category variance</Text>
                    </>
                  ),
                },
                {
                  color: 'green',
                  children: (
                    <>
                      <Text strong>Tomorrow · Sourcing council</Text>
                      <br />
                      <Text type="secondary">Approve vendor onboarding backlog</Text>
                    </>
                  ),
                },
                {
                  color: 'orange',
                  children: (
                    <>
                      <Text strong>Next Week · Contract audit</Text>
                      <br />
                      <Text type="secondary">Legal & compliance joint session</Text>
                    </>
                  ),
                },
                {
                  color: 'red',
                  children: (
                    <>
                      <Text strong>Quarter End · Savings report</Text>
                      <br />
                      <Text type="secondary">Publish realised vs planned benefits</Text>
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

export default ProcurementWorkspace;
