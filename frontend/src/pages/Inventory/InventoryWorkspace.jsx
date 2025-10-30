import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Button,
  Space,
  Progress,
  List,
  Tabs,
  Tag,
  Timeline,
  Typography,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  ShopOutlined,
  ClusterOutlined,
  AlertOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ApartmentOutlined,
  DeploymentUnitOutlined,
  GatewayOutlined,
  DatabaseOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Area, Column } from '@ant-design/charts';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useCompany } from '../../contexts/CompanyContext';
import api from '../../services/api';

const { Title, Paragraph, Text } = Typography;

const INITIAL_KPIS = [
  {
    key: 'inventory_value',
    label: 'Inventory Value',
    value: 12800000,
    suffix: 'BDT',
    trend: -4,
  },
  {
    key: 'fill_rate',
    label: 'Order Fill Rate',
    value: 96.4,
    suffix: '%',
    trend: 2,
  },
  {
    key: 'stockout_risk',
    label: 'Stockout Risk Items',
    value: 18,
    suffix: 'SKUs',
    trend: -6,
  },
  {
    key: 'carrying_cost',
    label: 'Carrying Cost / Month',
    value: 420000,
    suffix: 'BDT',
    trend: -3,
  },
];

const INITIAL_STOCK_COVERAGE = [
  { week: 'Week 1', type: 'Projected Demand', value: 4200 },
  { week: 'Week 1', type: 'Available Stock', value: 6100 },
  { week: 'Week 2', type: 'Projected Demand', value: 4600 },
  { week: 'Week 2', type: 'Available Stock', value: 5800 },
  { week: 'Week 3', type: 'Projected Demand', value: 5000 },
  { week: 'Week 3', type: 'Available Stock', value: 5600 },
  { week: 'Week 4', type: 'Projected Demand', value: 5200 },
  { week: 'Week 4', type: 'Available Stock', value: 5450 },
];

const INITIAL_ABC_BREAKDOWN = [
  { category: 'A', value: 55 },
  { category: 'B', value: 28 },
  { category: 'C', value: 17 },
];

const INITIAL_REPLENISH_BOARD = {
  columns: {
    'replenishment-watch': {
      id: 'replenishment-watch',
      title: 'Watch (Cover 4-7 days)',
      description: 'Plan replenishment this week',
      itemIds: ['sku-1003', 'sku-1011'],
    },
    'replenishment-critical': {
      id: 'replenishment-critical',
      title: 'Critical (Cover <3 days)',
      description: 'Escalate and expedite',
      itemIds: ['sku-1007', 'sku-1015', 'sku-1020'],
    },
    'replenishment-expedited': {
      id: 'replenishment-expedited',
      title: 'Expedited Inbound',
      description: 'In transit or waiting approval',
      itemIds: ['sku-1019'],
    },
  },
  items: {
    'sku-1003': {
      id: 'sku-1003',
      sku: 'FAB-ROLL-60',
      product: 'Cotton Fabric Roll 60 GSM',
      coverage: '5.5 days',
      owner: 'Procurement',
    },
    'sku-1011': {
      id: 'sku-1011',
      sku: 'BTN-PLASTIC',
      product: 'Shirt Buttons (Pack of 500)',
      coverage: '6.2 days',
      owner: 'Store Ops',
    },
    'sku-1007': {
      id: 'sku-1007',
      sku: 'DYE-NVY',
      product: 'Reactive Dye Navy Blue 5kg',
      coverage: '2.4 days',
      owner: 'Dyeing Unit',
    },
    'sku-1015': {
      id: 'sku-1015',
      sku: 'BOX-EXP',
      product: 'Export Carton Box',
      coverage: '1.8 days',
      owner: 'Logistics',
    },
    'sku-1020': {
      id: 'sku-1020',
      sku: 'ELAST-25',
      product: 'Elastic Band 25mm',
      coverage: '2.1 days',
      owner: 'Accessory Store',
    },
    'sku-1019': {
      id: 'sku-1019',
      sku: 'ZIP-NYLON',
      product: 'Nylon Zippers 18"',
      coverage: 'In Transit',
      owner: 'Inbound QA',
    },
  },
};

const INITIAL_TRANSFER_PIPELINE = [
  {
    id: 'transfer-1',
    title: 'TRANSFER-2305 · HQ → Fulfilment Centre',
    status: 'In Transit',
    eta: 'Arrives in 6 hours',
  },
  {
    id: 'transfer-2',
    title: 'TRANSFER-2306 · Print Unit → HQ',
    status: 'Awaiting Dispatch',
    eta: 'Scheduled for 4 PM',
  },
  {
    id: 'transfer-3',
    title: 'TRANSFER-2307 · EU Hub → HQ',
    status: 'Clearing Customs',
    eta: 'ETA +2 days',
  },
];

const INITIAL_AUTOMATIONS = [
  {
    id: 'auto-1',
    title: 'Visual Kanban Replenishment',
    detail: 'Auto-create purchase request at min stock, escalate if lead-time breached',
  },
  {
    id: 'auto-2',
    title: 'Cold Room IoT Alerts',
    detail: 'Trigger maintenance workflow if temperature deviates beyond ±2°C',
  },
  {
    id: 'auto-3',
    title: 'Cycle Count Scheduler',
    detail: 'Drag-and-drop assignments sync with handheld scanning app',
  },
];

const INITIAL_STOCK_LEDGER_SUMMARY = {
  totalSkusTracked: 1420,
  lastMovementAt: '2025-10-25T21:22:00Z',
  ledgerValue: 12800000,
  openDiscrepancies: 0,
};

const INITIAL_STOCK_EVENT_STREAM = [
  {
    id: 'stock-event-1',
    label: 'stock.received',
    reference: 'PO-2025-0041 / GRN-0778',
    journalImpact: 'Dr Inventory -> Cr GRNI',
    status: 'synced',
    timestamp: '2025-10-25 21:18',
  },
  {
    id: 'stock-event-2',
    label: 'stock.shipped',
    reference: 'SO-2025-0194 / SHP-0442',
    journalImpact: 'Dr COGS -> Cr Inventory',
    status: 'synced',
    timestamp: '2025-10-25 20:41',
  },
  {
    id: 'stock-event-3',
    label: 'stock.adjusted',
    reference: 'ADJ-2025-006',
    journalImpact: 'Dr Inventory Shrinkage -> Cr Inventory',
    status: 'pending',
    timestamp: '2025-10-25 19:58',
  },
];

const stockEventStatusColors = {
  synced: 'green',
  pending: 'blue',
  failed: 'red',
};

const InventoryWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [overviewKpis, setOverviewKpis] = useState(INITIAL_KPIS);
  const [stockCoverage, setStockCoverage] = useState(INITIAL_STOCK_COVERAGE);
  const [abcBreakdown, setAbcBreakdown] = useState(INITIAL_ABC_BREAKDOWN);
  const [replenishmentBoard, setReplenishmentBoard] = useState(INITIAL_REPLENISH_BOARD);
  const [transferPipeline, setTransferPipeline] = useState(INITIAL_TRANSFER_PIPELINE);
  const [automationRecipes, setAutomationRecipes] = useState(INITIAL_AUTOMATIONS);
  const [stockLedgerSummary, setStockLedgerSummary] = useState(INITIAL_STOCK_LEDGER_SUMMARY);
  const [stockEventStream, setStockEventStream] = useState(INITIAL_STOCK_EVENT_STREAM);

  useEffect(() => {
    const loadOverview = async () => {
      setLoading(true);
      try {
        if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
          setOverviewKpis(INITIAL_KPIS);
          setStockCoverage(INITIAL_STOCK_COVERAGE);
          setAbcBreakdown(INITIAL_ABC_BREAKDOWN);
          setReplenishmentBoard(JSON.parse(JSON.stringify(INITIAL_REPLENISH_BOARD)));
          setTransferPipeline(INITIAL_TRANSFER_PIPELINE);
          setAutomationRecipes(INITIAL_AUTOMATIONS);
          setStockLedgerSummary(INITIAL_STOCK_LEDGER_SUMMARY);
          setStockEventStream(INITIAL_STOCK_EVENT_STREAM);
          return;
        }

        const response = await api.get('/api/v1/inventory/overview/', {
          params: { company: currentCompany?.id },
        });
        const payload = response.data || {};

        setOverviewKpis(
          Array.isArray(payload.kpis) && payload.kpis.length ? payload.kpis : INITIAL_KPIS,
        );

        setStockCoverage(
          Array.isArray(payload.stock_coverage) && payload.stock_coverage.length
            ? payload.stock_coverage
            : INITIAL_STOCK_COVERAGE,
        );

        setAbcBreakdown(
          Array.isArray(payload.abc_breakdown) && payload.abc_breakdown.length
            ? payload.abc_breakdown
            : INITIAL_ABC_BREAKDOWN,
        );

        if (
          payload.replenishment_board &&
          payload.replenishment_board.columns &&
          payload.replenishment_board.items
        ) {
          setReplenishmentBoard(payload.replenishment_board);
        } else {
          setReplenishmentBoard(JSON.parse(JSON.stringify(INITIAL_REPLENISH_BOARD)));
        }

        setTransferPipeline(
          Array.isArray(payload.transfer_pipeline) && payload.transfer_pipeline.length
            ? payload.transfer_pipeline
            : INITIAL_TRANSFER_PIPELINE,
        );

        setAutomationRecipes(
          Array.isArray(payload.automations) && payload.automations.length
            ? payload.automations
            : INITIAL_AUTOMATIONS,
        );

        try {
          const ledgerResponse = await api.get('/api/v1/inventory/stock-ledger/summary/', {
            params: { company: currentCompany?.id },
          });
          const ledgerPayload = ledgerResponse.data || {};
          setStockLedgerSummary({
            totalSkusTracked:
              typeof ledgerPayload.total_skus_tracked === 'number'
                ? ledgerPayload.total_skus_tracked
                : INITIAL_STOCK_LEDGER_SUMMARY.totalSkusTracked,
            lastMovementAt: ledgerPayload.last_movement_at || INITIAL_STOCK_LEDGER_SUMMARY.lastMovementAt,
            ledgerValue:
              typeof ledgerPayload.ledger_value === 'number'
                ? ledgerPayload.ledger_value
                : INITIAL_STOCK_LEDGER_SUMMARY.ledgerValue,
            openDiscrepancies:
              typeof ledgerPayload.open_discrepancies === 'number'
                ? ledgerPayload.open_discrepancies
                : INITIAL_STOCK_LEDGER_SUMMARY.openDiscrepancies,
          });
        } catch (ledgerErr) {
          console.warn('Stock ledger summary fallback data used:', ledgerErr?.message);
          setStockLedgerSummary(INITIAL_STOCK_LEDGER_SUMMARY);
        }

        try {
          const eventResponse = await api.get('/api/v1/inventory/stock-ledger/events/', {
            params: { company: currentCompany?.id, limit: 10 },
          });
          const eventsPayload = eventResponse.data;
          const records = Array.isArray(eventsPayload?.results)
            ? eventsPayload.results
            : Array.isArray(eventsPayload)
              ? eventsPayload
              : [];
          setStockEventStream(
            records.length
              ? records.map((record, index) => ({
                  id: record.id || `stock-event-${index}`,
                  label: record.event || record.label || 'stock.event',
                  reference: record.reference || record.reference_code || '',
                  journalImpact:
                    record.journal_impact ||
                    record.description ||
                    INITIAL_STOCK_EVENT_STREAM[index % INITIAL_STOCK_EVENT_STREAM.length].journalImpact,
                  status: record.status || record.sync_state || 'synced',
                  timestamp: record.timestamp || record.created_at || '',
                }))
              : INITIAL_STOCK_EVENT_STREAM,
          );
        } catch (eventErr) {
          console.warn('Stock event stream fallback data used:', eventErr?.message);
          setStockEventStream(INITIAL_STOCK_EVENT_STREAM);
        }
      } catch (error) {
        console.warn('Inventory overview fallback data used:', error?.message);
        setOverviewKpis(INITIAL_KPIS);
        setStockCoverage(INITIAL_STOCK_COVERAGE);
        setAbcBreakdown(INITIAL_ABC_BREAKDOWN);
        setReplenishmentBoard(JSON.parse(JSON.stringify(INITIAL_REPLENISH_BOARD)));
        setTransferPipeline(INITIAL_TRANSFER_PIPELINE);
        setAutomationRecipes(INITIAL_AUTOMATIONS);
        setStockLedgerSummary(INITIAL_STOCK_LEDGER_SUMMARY);
        setStockEventStream(INITIAL_STOCK_EVENT_STREAM);
      } finally {
        setLoading(false);
      }
    };

    loadOverview();
  }, [currentCompany]);

  const stockCoverageConfig = useMemo(() => {
    const safeData = (Array.isArray(stockCoverage) ? stockCoverage : []).map((item) => ({
      ...item,
      value: Number(item?.value) || 0,
    }));
    return {
      data: safeData,
      xField: 'week',
      yField: 'value',
      seriesField: 'type',
      isGroup: true,
      columnStyle: {
        radius: [8, 8, 0, 0],
      },
      legend: { position: 'top' },
      color: ({ type }) => (type === 'Available Stock' ? '#73d13d' : '#597ef7'),
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: `${datum.value.toLocaleString()} units`,
        }),
      },
    };
  }, [stockCoverage]);

  const abcConfig = useMemo(() => {
    const safeData = (Array.isArray(abcBreakdown) ? abcBreakdown : []).map((item) => ({
      ...item,
      value: Number(item?.value) || 0,
    }));
    return {
      data: safeData,
      xField: 'category',
      yField: 'value',
      columnStyle: {
        radius: [10, 10, 0, 0],
      },
      color: ({ category }) => {
        if (category === 'A') return '#722ed1';
        if (category === 'B') return '#13c2c2';
        return '#faad14';
      },
      tooltip: {
        formatter: (datum) => ({
          name: `Class ${datum.category}`,
          value: `${datum.value}% of inventory value`,
        }),
      },
    };
  }, [abcBreakdown]);

  const stockLedgerValueDisplay = useMemo(() => {
    const value = Number(stockLedgerSummary?.ledgerValue ?? INITIAL_STOCK_LEDGER_SUMMARY.ledgerValue);
    if (Number.isNaN(value)) {
      return INITIAL_STOCK_LEDGER_SUMMARY.ledgerValue;
    }
    return value;
  }, [stockLedgerSummary]);

  const stockLedgerLastMovement = useMemo(() => {
    if (!stockLedgerSummary?.lastMovementAt) {
      return 'No movement yet';
    }
    const parsed = new Date(stockLedgerSummary.lastMovementAt);
    if (Number.isNaN(parsed.getTime())) {
      return stockLedgerSummary.lastMovementAt;
    }
    return parsed.toLocaleString();
  }, [stockLedgerSummary]);

  const recentStockEvents = useMemo(
    () => (Array.isArray(stockEventStream) ? stockEventStream.slice(0, 5) : []),
    [stockEventStream],
  );

  const openDiscrepancies = useMemo(() => {
    const value =
      typeof stockLedgerSummary?.openDiscrepancies === 'number'
        ? stockLedgerSummary.openDiscrepancies
        : INITIAL_STOCK_LEDGER_SUMMARY.openDiscrepancies;
    return value;
  }, [stockLedgerSummary]);

  const totalSkusTracked = useMemo(() => {
    const value =
      typeof stockLedgerSummary?.totalSkusTracked === 'number'
        ? stockLedgerSummary.totalSkusTracked
        : INITIAL_STOCK_LEDGER_SUMMARY.totalSkusTracked;
    return value;
  }, [stockLedgerSummary]);

  const boardTotals = useMemo(() => {
    const totals = {};
    Object.values(replenishmentBoard.columns).forEach((column) => {
      totals[column.id] = column.itemIds.length;
    });
    return totals;
  }, [replenishmentBoard]);

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

    setReplenishmentBoard((prev) => {
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
      const newStartColumn = {
        ...startColumn,
        itemIds: startItemIds,
      };

      const finishItemIds = Array.from(finishColumn.itemIds);
      finishItemIds.splice(destination.index, 0, draggableId);
      const newFinishColumn = {
        ...finishColumn,
        itemIds: finishItemIds,
      };

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
        Inventory Control Tower{' '}
        {currentCompany?.name ? (
          <Text type="secondary">· {currentCompany.name}</Text>
        ) : null}
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 780 }}>
        Balance stock levels, orchestrate transfers, and automate replenishment with the
        Twist ERP visual inventory workspace. Monitor critical KPIs, heat maps, and
        drag-and-drop boards for replenishment execution.
      </Paragraph>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {overviewKpis.map((item) => (
          <Col key={item.key} xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Space direction="vertical" size={4}>
                <Text type="secondary">{item.label}</Text>
                <Statistic
                  value={item.value}
                  suffix={item.suffix}
                  precision={item.key === 'fill_rate' ? 1 : 0}
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
        <Col xs={24} lg={8}>
          <Card title="Stock Ledger Overview" loading={loading}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space align="baseline">
                <DatabaseOutlined style={{ fontSize: 28, color: '#73d13d' }} />
                <Statistic
                  value={stockLedgerValueDisplay}
                  prefix="BDT"
                  valueStyle={{ fontSize: 24 }}
                />
              </Space>
              <Space>
                <Tag color="blue">Tracked SKUs: {totalSkusTracked}</Tag>
                <Tag color={openDiscrepancies ? 'red' : 'green'}>
                  {openDiscrepancies
                    ? `${openDiscrepancies} discrepancies`
                    : 'No open discrepancies'}
                </Tag>
              </Space>
              <Text type="secondary">Last movement: {stockLedgerLastMovement}</Text>
              <Text type="secondary">
                Every goods receipt, transfer, or shipment writes an immutable StockLedgerEntry.
              </Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Ledger Sync Status" loading={loading}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Progress
                percent={openDiscrepancies ? 92 : 100}
                status={openDiscrepancies ? 'active' : 'success'}
              />
              <Space>
                <SafetyCertificateOutlined
                  style={{
                    color: openDiscrepancies ? '#fa8c16' : '#52c41a',
                    fontSize: 18,
                  }}
                />
                <Text type="secondary">
                  JournalEntryService posts valuation updates after each stock event.
                </Text>
              </Space>
              <Text type="secondary">
                Last sync with finance: {stockLedgerLastMovement}
              </Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Finance Bridge Events" loading={loading}>
            <List
              size="small"
              dataSource={recentStockEvents}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <GatewayOutlined style={{ color: '#597ef7' }} />
                      <Text strong>{item.label}</Text>
                      <Tag color={stockEventStatusColors[item.status] || 'blue'}>
                        {(item.status || 'synced').toUpperCase()}
                      </Tag>
                    </Space>
                    <Text type="secondary">{item.journalImpact}</Text>
                    {item.reference ? <Text type="secondary">Ref: {item.reference}</Text> : null}
                    {item.timestamp ? <Text type="secondary">{item.timestamp}</Text> : null}
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
            title="Stock Coverage vs Demand"
            loading={loading}
            extra={
              <Space>
                <Button icon={<ReloadOutlined />}>Re-run Forecast</Button>
                <Button icon={<ThunderboltOutlined />} type="primary">
                  Create Scenario
                </Button>
              </Space>
            }
          >
            <Column {...stockCoverageConfig} height={320} />
          </Card>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title="ABC Contribution" loading={loading}>
                <Column {...abcConfig} height={240} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Health Indicators" loading={loading}>
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">Perfect Order Rate</Text>
                    <Progress percent={92} status="active" />
                  </div>
                  <div>
                    <Space align="baseline">
                      <ShopOutlined style={{ fontSize: 32, color: '#13c2c2' }} />
                      <Space direction="vertical" size={0}>
                        <Text type="secondary">Capacity Utilization</Text>
                        <Title level={4} style={{ margin: 0 }}>
                          78% across network
                        </Title>
                      </Space>
                    </Space>
                  </div>
                  <div>
                    <Space align="baseline">
                      <ClusterOutlined style={{ fontSize: 32, color: '#faad14' }} />
                      <Space direction="vertical" size={0}>
                        <Text type="secondary">Aged Inventory</Text>
                        <Title level={4} style={{ margin: 0 }}>
                          6.8% &gt; 90 days
                        </Title>
                      </Space>
                    </Space>
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>

          <Card
            title="Replenishment Board"
            style={{ marginTop: 16 }}
            extra={<Text type="secondary">Drag SKUs to reprioritize actions</Text>}
          >
            <DragDropContext onDragEnd={handleDragEnd}>
              <Row gutter={[16, 16]}>
                {Object.values(replenishmentBoard.columns).map((column) => (
                  <Col xs={24} lg={8} key={column.id}>
                    <Card
                      title={
                        <Space>
                          {column.title}
                          <Tag>{boardTotals[column.id]} SKUs</Tag>
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
                              background: snapshot.isDraggingOver ? '#f6ffed' : 'transparent',
                              borderRadius: 8,
                              padding: 4,
                              transition: 'background-color 0.2s ease',
                            }}
                          >
                            {column.itemIds.map((itemId, index) => {
                              const item = replenishmentBoard.items[itemId];
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
                                          ? '0 8px 16px rgba(82, 196, 26, 0.25)'
                                          : '0 1px 3px rgba(0,0,0,0.08)',
                                        border: '1px solid #f0f0f0',
                                      }}
                                    >
                                      <Space direction="vertical" size={0} style={{ width: '100%' }}>
                                        <Space
                                          style={{ justifyContent: 'space-between', width: '100%' }}
                                          align="baseline"
                                        >
                                          <Text strong>{item.product}</Text>
                                          <Tag color="blue">{item.coverage}</Tag>
                                        </Space>
                                        <Space
                                          align="baseline"
                                          style={{ justifyContent: 'space-between', width: '100%' }}
                                        >
                                          <Text type="secondary">{item.sku}</Text>
                                          <Tag color="purple">{item.owner}</Tag>
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
          <Card title="Network Snapshot" style={{ marginBottom: 16 }} loading={loading}>
            <List
              dataSource={[
                {
                  id: 'ns-1',
                  label: 'HQ Distribution',
                  value: '81% capacity',
                  description: 'Cross-dock lanes normal',
                },
                {
                  id: 'ns-2',
                  label: 'Print Unit Store',
                  value: '68% capacity',
                  description: 'Dye chemicals low – restock scheduled',
                },
                {
                  id: 'ns-3',
                  label: 'EU Hub',
                  value: '54% capacity',
                  description: 'Awaiting inbound container',
                },
              ]}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Space>
                      <ApartmentOutlined style={{ color: '#1890ff' }} />
                      <Text strong>{item.label}</Text>
                    </Space>
                    <Text>{item.value}</Text>
                    <Text type="secondary">{item.description}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Card title="Transfer Pipeline" style={{ marginBottom: 16 }} loading={loading}>
            <List
              dataSource={transferPipeline}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0}>
                    <Space>
                      <DeploymentUnitOutlined style={{ color: '#52c41a' }} />
                      <Text strong>{item.title}</Text>
                    </Space>
                    <Text type="secondary">{item.status}</Text>
                    <Text>{item.eta}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Tabs
            defaultActiveKey="alerts"
            items={[
              {
                key: 'alerts',
                label: 'Alerts',
                children: (
                  <List
                    dataSource={[
                      {
                        id: 'alert-1',
                        title: 'Cycle count overdue · Print Unit',
                        severity: 'warning',
                      },
                      {
                        id: 'alert-2',
                        title: 'Cold storage temperature variance detected',
                        severity: 'critical',
                      },
                      {
                        id: 'alert-3',
                        title: 'New SKU from Sales awaiting slotting',
                        severity: 'info',
                      },
                    ]}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space>
                          <AlertOutlined
                            style={{ color: item.severity === 'critical' ? '#f5222d' : '#faad14' }}
                          />
                          <Text>{item.title}</Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
              {
                key: 'automations',
                label: 'Automations',
                children: (
                  <List
                    dataSource={automationRecipes}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space direction="vertical" size={0}>
                          <Space>
                            <ThunderboltOutlined style={{ color: '#722ed1' }} />
                            <Text strong>{item.title}</Text>
                          </Space>
                          <Text type="secondary">{item.detail}</Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
          />

          <Card title="Wave & Task Calendar" style={{ marginTop: 16 }}>
            <Timeline
              items={[
                {
                  color: 'green',
                  children: (
                    <>
                      <Text strong>08:00 · Receiving Wave 1</Text>
                      <br />
                      <Text type="secondary">3 containers · 156 pallets</Text>
                    </>
                  ),
                },
                {
                  color: 'blue',
                  children: (
                    <>
                      <Text strong>11:30 · Cycle Count Zone B</Text>
                      <br />
                      <Text type="secondary">Assigned to Team Delta</Text>
                    </>
                  ),
                },
                {
                  color: 'orange',
                  children: (
                    <>
                      <Text strong>14:00 · Pick Wave #27</Text>
                      <br />
                      <Text type="secondary">132 orders · express priority</Text>
                    </>
                  ),
                },
                {
                  color: 'red',
                  children: (
                    <>
                      <Text strong>16:30 · Hazardous Materials Audit</Text>
                      <br />
                      <Text type="secondary">Compliance checklist review</Text>
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

export default InventoryWorkspace;
