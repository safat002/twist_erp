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
  Progress,
  Divider,
} from 'antd';
import {
  TeamOutlined,
  SmileOutlined,
  ScheduleOutlined,
  SolutionOutlined,
  AuditOutlined,
  ThunderboltOutlined,
  UserSwitchOutlined,
  DollarOutlined,
  AlertOutlined,
  SafetyCertificateOutlined,
  FieldTimeOutlined,
} from '@ant-design/icons';
import { Area, Column } from '@ant-design/charts';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useCompany } from '../../contexts/CompanyContext';
import api from '../../services/api';

const { Title, Paragraph, Text } = Typography;

const INITIAL_KPIS = [
  { key: 'headcount', label: 'Total Headcount', value: 1260, suffix: '', trend: 3 },
  { key: 'attendance', label: 'Attendance Today', value: 94.5, suffix: '%', trend: 1.2 },
  { key: 'attrition', label: 'Attrition YTD', value: 8.4, suffix: '%', trend: -0.5 },
  { key: 'payroll', label: 'Payroll Compliance', value: 99.2, suffix: '%', trend: 0.8 },
];

const INITIAL_HEADCOUNT_TREND = [
  { month: 'Jan', headcount: 1190, attrition: 1.1 },
  { month: 'Feb', headcount: 1205, attrition: 0.9 },
  { month: 'Mar', headcount: 1222, attrition: 1.0 },
  { month: 'Apr', headcount: 1238, attrition: 0.8 },
  { month: 'May', headcount: 1250, attrition: 0.7 },
  { month: 'Jun', headcount: 1260, attrition: 0.7 },
];

const INITIAL_PULSE_RESULTS = [
  { category: 'Engagement', value: 78 },
  { category: 'Manager Index', value: 84 },
  { category: 'Wellness', value: 72 },
  { category: 'Growth', value: 81 },
];

const INITIAL_PEOPLE_BOARD = {
  columns: {
    pipeline: {
      id: 'pipeline',
      title: 'Talent Pipeline',
      description: 'Candidates + requisitions',
      itemIds: ['people-101', 'people-104'],
    },
    onboarding: {
      id: 'onboarding',
      title: 'Onboarding',
      description: 'In progress orientation & training',
      itemIds: ['people-205'],
    },
    performance: {
      id: 'performance',
      title: 'Performance',
      description: 'Reviews & development plans',
      itemIds: ['people-302', 'people-304'],
    },
    retention: {
      id: 'retention',
      title: 'Retention',
      description: 'High-potential & succession',
      itemIds: ['people-401'],
    },
  },
  items: {
    'people-101': {
      id: 'people-101',
      name: 'Data Analyst (HQ)',
      owner: 'Talent Acquisition',
      stage: 'Interviews scheduled',
    },
    'people-104': {
      id: 'people-104',
      name: 'Production Supervisor (Unit 3)',
      owner: 'Manufacturing',
      stage: 'Offer draft',
    },
    'people-205': {
      id: 'people-205',
      name: 'New Merchandising Cohort',
      owner: 'L&D',
      stage: 'Week 2 orientation',
    },
    'people-302': {
      id: 'people-302',
      name: 'Quarterly Reviews',
      owner: 'HR Business Partners',
      stage: '65% complete',
    },
    'people-304': {
      id: 'people-304',
      name: 'Leadership Development Batch',
      owner: 'People Ops',
      stage: 'Assessments ongoing',
    },
    'people-401': {
      id: 'people-401',
      name: 'Attrition Watchlist',
      owner: 'HR Analytics',
      stage: '3 employees flagged',
    },
  },
};

const INITIAL_CAPACITY_OVERVIEW = {
  window: { start: null, end: null, days: 7 },
  totals: {
    requiredHeadcount: 0,
    actualHeadcount: 0,
    plannedOvertimeHours: 0,
    actualOvertimeHours: 0,
    qaRequiredHeadcount: 0,
    qaActualHeadcount: 0,
    qaVariance: 0,
  },
  scenarios: [],
  plans: [],
  qaAlerts: [],
};

const INITIAL_OVERTIME_DASHBOARD = {
  window: { start: null, end: null, days: 30 },
  approvedHours: 0,
  approvedAmount: 0,
  pendingApprovals: 0,
  recent: [],
};

const INITIAL_PAYROLL_RUNS = [
  {
    id: 'pay-1',
    period: 'Sep 2025',
    processedOn: '25 Sep @ 18:30',
    amount: 'BDT 32.4M',
    status: 'Completed',
  },
  {
    id: 'pay-2',
    period: 'Oct 2025',
    processedOn: 'Scheduled @ 25 Oct',
    amount: 'BDT 33.1M',
    status: 'Scheduled',
  },
  {
    id: 'pay-3',
    period: 'Nov 2025',
    processedOn: 'Draft',
    amount: 'BDT 33.8M',
    status: 'Draft',
  },
];

const INITIAL_ALERTS = [
  {
    id: 'alert-1',
    message: 'Overtime spike detected in Printing Unit (+18%)',
    severity: 'warning',
  },
  {
    id: 'alert-2',
    message: '3 payroll exceptions pending approval',
    severity: 'critical',
  },
  {
    id: 'alert-3',
    message: 'Mandatory compliance training due for 24 employees',
    severity: 'info',
  },
];

const INITIAL_AUTOMATIONS = [
  {
    id: 'auto-1',
    title: 'Auto-generate payroll journals',
    detail: 'Posts salary + statutory accruals to ledger',
    status: 'active',
  },
  {
    id: 'auto-2',
    title: 'Attendance anomaly alert',
    detail: 'Flags >10% variance in shift adherence',
    status: 'active',
  },
  {
    id: 'auto-3',
    title: 'Onboarding checklist',
    detail: 'Drag components to design role-specific flows',
    status: 'beta',
  },
];

const severityColors = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};

const HRWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState(INITIAL_KPIS);
  const [headcountTrend, setHeadcountTrend] = useState(INITIAL_HEADCOUNT_TREND);
  const [pulseResults, setPulseResults] = useState(INITIAL_PULSE_RESULTS);
  const [board, setBoard] = useState(INITIAL_PEOPLE_BOARD);
  const [payrollRuns, setPayrollRuns] = useState(INITIAL_PAYROLL_RUNS);
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [automations, setAutomations] = useState(INITIAL_AUTOMATIONS);
  const [capacityOverview, setCapacityOverview] = useState(INITIAL_CAPACITY_OVERVIEW);
  const [overtimeDashboard, setOvertimeDashboard] = useState(INITIAL_OVERTIME_DASHBOARD);

  useEffect(() => {
    const fetchOverview = async () => {
      setLoading(true);
      try {
        const response = await api.get('/api/v1/hr/overview/', {
          params: { company: currentCompany?.id },
        });
        const payload = response.data || {};

        if (Array.isArray(payload.kpis) && payload.kpis.length) {
          setKpis(payload.kpis);
        } else {
          setKpis(INITIAL_KPIS);
        }

        setHeadcountTrend(
          Array.isArray(payload.headcount_trend) && payload.headcount_trend.length
            ? payload.headcount_trend
            : INITIAL_HEADCOUNT_TREND,
        );

        setPulseResults(
          Array.isArray(payload.pulse_results) && payload.pulse_results.length
            ? payload.pulse_results
            : INITIAL_PULSE_RESULTS,
        );

        if (payload.people_board && payload.people_board.columns && payload.people_board.items) {
          setBoard(payload.people_board);
        } else {
          setBoard(JSON.parse(JSON.stringify(INITIAL_PEOPLE_BOARD)));
        }

        setPayrollRuns(
          Array.isArray(payload.payroll_runs) && payload.payroll_runs.length
            ? payload.payroll_runs
            : INITIAL_PAYROLL_RUNS,
        );

        setAlerts(
          Array.isArray(payload.alerts) && payload.alerts.length ? payload.alerts : INITIAL_ALERTS,
        );

        setAutomations(
          Array.isArray(payload.automations) && payload.automations.length
            ? payload.automations
            : INITIAL_AUTOMATIONS,
        );
      } catch (error) {
        console.warn('HR overview fallback data used:', error?.message);
        setKpis(INITIAL_KPIS);
        setHeadcountTrend(INITIAL_HEADCOUNT_TREND);
        setPulseResults(INITIAL_PULSE_RESULTS);
        setBoard(JSON.parse(JSON.stringify(INITIAL_PEOPLE_BOARD)));
        setPayrollRuns(INITIAL_PAYROLL_RUNS);
        setAlerts(INITIAL_ALERTS);
        setAutomations(INITIAL_AUTOMATIONS);
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, [currentCompany?.id]);

  const headcountConfig = useMemo(() => {
    const data = Array.isArray(headcountTrend)
      ? headcountTrend.reduce((acc, entry) => {
          acc.push({
            month: entry.month,
            type: 'Headcount',
            value: Number(entry.headcount) || 0,
          });
          acc.push({
            month: entry.month,
            type: 'Attrition %',
            value: Number(entry.attrition) || 0,
          });
          return acc;
        }, [])
      : [];

    return {
      data,
      xField: 'month',
      yField: 'value',
      seriesField: 'type',
      smooth: true,
      color: ({ type }) => (type === 'Headcount' ? '#1890ff' : '#fa8c16'),
      tooltip: {
        formatter: (datum) => ({
          name: datum.type,
          value: datum.type === 'Headcount' ? datum.value : `${datum.value.toFixed(2)}%`,
        }),
      },
    };
  }, [headcountTrend]);

  const pulseConfig = useMemo(() => {
    const data = (Array.isArray(pulseResults) ? pulseResults : []).map((item) => ({
      ...item,
      value: Number(item?.value) || 0,
    }));

    return {
      data,
      xField: 'category',
      yField: 'value',
      columnStyle: { radius: [8, 8, 0, 0] },
      color: '#52c41a',
      tooltip: {
        formatter: (datum) => ({
          name: datum.category,
          value: `${datum.value}/100`,
        }),
      },
    };
  }, [pulseResults]);

  const capacityTotals = useMemo(() => {
    const totals = capacityOverview?.totals || {};
    const required = Number(totals.requiredHeadcount) || 0;
    const actual = Number(totals.actualHeadcount) || 0;
    const plannedOvertime = Number(totals.plannedOvertimeHours) || 0;
    const actualOvertime = Number(totals.actualOvertimeHours) || 0;
    const qaRequired = Number(totals.qaRequiredHeadcount) || 0;
    const qaActual = Number(totals.qaActualHeadcount) || 0;
    const qaVariance = Number(totals.qaVariance ?? qaActual - qaRequired) || 0;
    const utilization = required > 0 ? (actual / required) * 100 : 0;
    const qaCoverage = qaRequired > 0 ? (qaActual / qaRequired) * 100 : 100;

    return {
      required,
      actual,
      plannedOvertime,
      actualOvertime,
      qaRequired,
      qaActual,
      qaVariance,
      utilization,
      qaCoverage,
    };
  }, [capacityOverview]);

  const scenarioBreakdown = useMemo(
    () =>
      Array.isArray(capacityOverview?.scenarios)
        ? capacityOverview.scenarios.map((item) => ({
            ...item,
            requiredHeadcount: Number(item.requiredHeadcount) || 0,
            actualHeadcount: Number(item.actualHeadcount) || 0,
          }))
        : [],
    [capacityOverview],
  );

  const qaAlerts = useMemo(
    () => (Array.isArray(capacityOverview?.qaAlerts) ? capacityOverview.qaAlerts : []),
    [capacityOverview],
  );

  const topPlans = useMemo(
    () => (Array.isArray(capacityOverview?.plans) ? capacityOverview.plans.slice(0, 4) : []),
    [capacityOverview],
  );


  const formatNumber = (value, options = {}) => {
    const numeric = Number(value || 0);
    return Number.isFinite(numeric)
      ? numeric.toLocaleString(undefined, {
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
          ...options,
        })
      : '0';
  };

  const formatAmount = (value) => {
    const numeric = Number(value || 0);
    return Number.isFinite(numeric)
      ? numeric.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : '0.00';
  };

  const formatDateRange = (window) => {
    if (!window || !window.start || !window.end) {
      return '';
    }
    try {
      const startDate = new Date(window.start);
      const endDate = new Date(window.end);
      return `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;
    } catch (err) {
      return '';
    }
  };

  const overtimeStats = useMemo(() => {
    const dashboard = overtimeDashboard || {};
    return {
      approvedHours: Number(dashboard.approvedHours) || 0,
      approvedAmount: Number(dashboard.approvedAmount) || 0,
      pendingApprovals: Number(dashboard.pendingApprovals) || 0,
      recent: Array.isArray(dashboard.recent) ? dashboard.recent : [],
      window: dashboard.window || { start: null, end: null, days: 30 },
    };
  }, [overtimeDashboard]);

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
        People Operations & Payroll Hub{' '}
        {currentCompany?.name ? <Text type="secondary">| {currentCompany.name}</Text> : null}
      </Title>
      <Paragraph type="secondary" style={{ maxWidth: 780 }}>
        Keep teams engaged and payroll precise. Blend workforce analytics, attendance, onboarding,
        and pay cycles in a unified, visual workspace.
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
                  precision={item.key === 'headcount' ? 0 : 1}
                  valueStyle={{ fontSize: 24 }}
                />
                <Space size={4}>
                  <TeamOutlined style={{ color: item.trend >= 0 ? '#52c41a' : '#f5222d' }} />
                  <Text type={item.trend >= 0 ? 'success' : 'danger'}>
                    {item.trend > 0 ? '+' : ''}
                    {item.trend}%
                  </Text>
                  <Text type="secondary">vs last month</Text>
                </Space>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card
            title="Headcount & Attrition Trend"
            extra={<Button size="small" icon={<UserSwitchOutlined />}>Update Org Plan</Button>}
            loading={loading}
          >
            <Area {...headcountConfig} height={320} />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card
            title={
              <Space>
                <SmileOutlined />
                Engagement Pulse
              </Space>
            }
            loading={loading}
          >
            <Column {...pulseConfig} height={240} />
          </Card>
          <Card title="Alerts & Exceptions" style={{ marginTop: 16 }} loading={loading}>
            <List
              dataSource={alerts}
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
        title="Workforce Board"
        style={{ marginTop: 16 }}
        extra={<Text type="secondary">Drag cohorts between talent, onboarding, and retention flows</Text>}
      >
        <DragDropContext onDragEnd={handleDragEnd}>
          <Row gutter={[16, 16]}>
            {Object.values(board.columns).map((column) => (
              <Col xs={24} md={12} xl={6} key={column.id}>
                <Card
                  title={
                    <Space>
                      <SolutionOutlined />
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
                          background: snapshot.isDraggingOver ? '#f6ffed' : 'transparent',
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
                                      ? '0 8px 16px rgba(82, 196, 26, 0.25)'
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
                                    <Text type="secondary">{card.stage}</Text>
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
        <Col xs={24} lg={16}>
          <Card
            title="Capacity Outlook"
            loading={loading}
            extra={<Text type="secondary">{formatDateRange(capacityOverview?.window)}</Text>}
          >
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Statistic title="Required Headcount" value={capacityTotals.required} />
              </Col>
              <Col xs={24} sm={12}>
                <Statistic
                  title="Actual Headcount"
                  value={capacityTotals.actual}
                  valueStyle={{ color: capacityTotals.utilization >= 100 ? '#52c41a' : '#1890ff' }}
                />
              </Col>
            </Row>
            <Divider />
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Text strong>Utilization</Text>
                <Progress
                  percent={Number(capacityTotals.utilization.toFixed(1))}
                  status={capacityTotals.utilization >= 100 ? 'success' : 'active'}
                />
              </Col>
              <Col xs={24} sm={12}>
                <Text strong>QA Coverage</Text>
                <Progress
                  percent={Number(Math.max(0, Math.min(100, capacityTotals.qaCoverage)).toFixed(1))}
                  status={
                    capacityTotals.qaCoverage >= 95
                      ? 'success'
                      : capacityTotals.qaCoverage >= 80
                      ? 'active'
                      : 'exception'
                  }
                />
              </Col>
            </Row>
            <Space direction="vertical" size="middle" style={{ width: '100%', marginTop: 16 }}>
              <Text strong>Scenario Breakdown</Text>
              <List
                dataSource={scenarioBreakdown}
                split={false}
                renderItem={(item) => (
                  <List.Item key={item.scenario}>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space>
                        <ScheduleOutlined style={{ color: '#1677ff' }} />
                        <Text strong>{item.scenario}</Text>
                      </Space>
                      <Text type="secondary">
                        {formatNumber(item.actualHeadcount)} / {formatNumber(item.requiredHeadcount)} headcount
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Space>
            <Divider />
            <Text strong>Upcoming Plans</Text>
            <List
              dataSource={topPlans}
              locale={{ emptyText: 'No capacity plans logged for this window.' }}
              renderItem={(plan) => (
                <List.Item key={plan.id || `${plan.shiftId}-${plan.date}`}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <FieldTimeOutlined style={{ color: '#722ed1' }} />
                      <Text strong>{plan.shiftCode || plan.shiftId}</Text>
                      <Tag>{plan.scenario}</Tag>
                    </Space>
                    <Text type="secondary">
                      Need {formatNumber(plan.requiredHeadcount)} � Actual {formatNumber(plan.actualHeadcount ?? 0)}
                    </Text>
                    {plan.notes ? <Text>{plan.notes}</Text> : null}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            title="QA Coverage Alerts"
            loading={loading}
            extra={<Tag color={qaAlerts.length ? 'red' : 'green'}>{qaAlerts.length || 0}</Tag>}
          >
            {qaAlerts.length === 0 ? (
              <Paragraph type="secondary">No QA coverage gaps flagged. ??</Paragraph>
            ) : (
              <List
                dataSource={qaAlerts}
                renderItem={(alert) => (
                  <List.Item key={alert.id || `${alert.shiftCode}-${alert.date}`}>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space>
                        <SafetyCertificateOutlined style={{ color: '#fa541c' }} />
                        <Text strong>{alert.shiftCode || alert.shiftId}</Text>
                        {alert.date ? <Tag>{alert.date}</Tag> : null}
                      </Space>
                      <Text type="secondary">{alert.notes || 'QA headcount below requirement.'}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title="Overtime Health"
            loading={loading}
            extra={<Text type="secondary">{formatDateRange(overtimeStats.window)}</Text>}
          >
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Statistic title="Approved Hours" value={overtimeStats.approvedHours} />
              </Col>
              <Col xs={24} sm={12}>
                <Statistic title="Approved Amount" value={formatAmount(overtimeStats.approvedAmount)} />
              </Col>
            </Row>
            <Divider />
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                <Text strong>Pending Approvals</Text>
                <Tag color={overtimeStats.pendingApprovals ? 'orange' : 'green'}>
                  {overtimeStats.pendingApprovals}
                </Tag>
              </Space>
              <List
                dataSource={overtimeStats.recent}
                locale={{ emptyText: 'No recent overtime entries.' }}
                renderItem={(entry) => (
                  <List.Item key={entry.id}>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space>
                        <ScheduleOutlined style={{ color: '#13c2c2' }} />
                        <Text strong>{entry.employee}</Text>
                        <Tag>{entry.hours}h</Tag>
                        <Tag color={entry.status === 'Approved' ? 'green' : 'blue'}>{entry.status}</Tag>
                      </Space>
                      <Text type="secondary">
                        {entry.date ? new Date(entry.date).toLocaleDateString() : ''} � {formatAmount(entry.amount)}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Capacity Notes" loading={loading}>
            <List
              dataSource={topPlans.length ? topPlans : scenarioBreakdown.slice(0, 3)}
              locale={{ emptyText: 'No capacity notes available.' }}
              renderItem={(item) => (
                <List.Item key={item.id || item.scenario}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Text strong>{item.shiftCode || item.scenario}</Text>
                    <Text type="secondary">
                      Required {formatNumber(item.requiredHeadcount || 0)} � Actual {formatNumber(item.actualHeadcount || 0)}
                    </Text>
                    {item.notes ? <Text>{item.notes}</Text> : null}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card
            title="Payroll Runs"
            extra={<Button icon={<DollarOutlined />}>View Ledger Entries</Button>}
            loading={loading}
          >
            <List
              dataSource={payrollRuns}
              renderItem={(item) => (
                <List.Item key={item.id}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space>
                      <AuditOutlined style={{ color: '#1890ff' }} />
                      <Text strong>{item.period}</Text>
                      <Tag color="blue">{item.amount}</Tag>
                    </Space>
                    <Text type="secondary">{item.processedOn}</Text>
                    <Tag color={item.status === 'Completed' ? 'green' : item.status === 'Scheduled' ? 'gold' : 'default'}>
                      {item.status.toUpperCase()}
                    </Tag>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card
            title="Automation Recipes"
            extra={<Button size="small" icon={<ThunderboltOutlined />}>New Automation</Button>}
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
          <Card title="People Calendar" style={{ marginTop: 16 }} loading={loading}>
            <Timeline
              items={[
                {
                  color: '#1890ff',
                  children: (
                    <Space direction="vertical" size={0}>
                      <Text strong>26 Oct - Payroll Cutoff</Text>
                      <Text type="secondary">Freeze changes & approve overtime</Text>
                    </Space>
                  ),
                },
                {
                  color: '#faad14',
                  children: (
                    <Space direction="vertical" size={0}>
                      <Text strong>30 Oct - Performance Reviews</Text>
                      <Text type="secondary">Managers finalize scores in Twist HR</Text>
                    </Space>
                  ),
                },
                {
                  color: '#52c41a',
                  children: (
                    <Space direction="vertical" size={0}>
                      <Text strong>05 Nov - Engagement Survey</Text>
                      <Text type="secondary">Pulse questionnaire opens for 2 weeks</Text>
                    </Space>
                  ),
                },
                {
                  color: '#722ed1',
                  children: (
                    <Space direction="vertical" size={0}>
                      <Text strong>15 Nov - L&D Sprint</Text>
                      <Text type="secondary">Upskill sessions for supervisors</Text>
                    </Space>
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

export default HRWorkspace;











