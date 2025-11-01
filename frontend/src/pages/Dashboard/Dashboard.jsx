import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  List,
  message,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
} from 'antd';
import {
  DollarOutlined,
  ShoppingCartOutlined,
  RiseOutlined,
  AlertOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { Responsive, WidthProvider } from 'react-grid-layout';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

import PageHeader from '../../components/Common/PageHeader';
import StatCard from '../../components/Common/StatCard';
import DataTable from '../../components/Common/DataTable';
import api from '../../services/api';
import { trackMetadataInterest } from '../../services/ai';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
);

const ResponsiveGridLayout = WidthProvider(Responsive);
const { Text } = Typography;

const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '30 days', value: '30d' },
  { label: '90 days', value: '90d' },
  { label: 'This Month', value: 'this_month' },
];

const defaultLayouts = {
  lg: [],
  md: [],
  sm: [],
  xs: [],
  xxs: [],
};

const formatCurrency = (value, currency = 'BDT') =>
  `${currency} ${Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

const formatNumber = (value) => Number(value || 0).toLocaleString();

const mapTrendPercentage = (series) => {
  if (!Array.isArray(series) || series.length < 2) return null;
  const start = series[0]?.total ?? series[0]?.net ?? series[0]?.value ?? 0;
  const end = series[series.length - 1]?.total ?? series[series.length - 1]?.net ?? series[series.length - 1]?.value ?? 0;
  if (!start) return null;
  return Number((((end - start) / start) * 100).toFixed(1));
};

const buildLineDataset = (series, label, color) => ({
  labels: series.map((item) => item.date),
  datasets: [
    {
      label,
      data: series.map((item) => item.total ?? item.value ?? 0),
      borderColor: color,
      backgroundColor: `${color}40`,
      fill: true,
      tension: 0.3,
    },
  ],
});

const buildCashflowDataset = (series) => ({
  labels: series.map((item) => item.date),
  datasets: [
    {
      label: 'Cash In',
      data: series.map((item) => item.cash_in ?? 0),
      backgroundColor: '#36cfc9',
    },
    {
      label: 'Cash Out',
      data: series.map((item) => item.cash_out ?? 0),
      backgroundColor: '#ff7875',
    },
    {
      label: 'Net',
      type: 'line',
      fill: false,
      borderColor: '#722ed1',
      data: series.map((item) => item.net ?? 0),
    },
  ],
});

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [widgets, setWidgets] = useState([]);
  const [layouts, setLayouts] = useState(defaultLayouts);
  const [availableWidgets, setAvailableWidgets] = useState([]);
  const [period, setPeriod] = useState('30d');
  const [savingLayout, setSavingLayout] = useState(false);
  const [scopeType, setScopeType] = useState('COMPANY');
  const [publishNow, setPublishNow] = useState(true);
  const [currency, setCurrency] = useState('BDT');
  const [myTasks, setMyTasks] = useState([]);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/v1/dashboard/', {
        params: { period },
      });
      setWidgets(data.widgets || []);
      setAvailableWidgets(data.available_widgets || []);
      setLayouts(data.layout || defaultLayouts);
      if (data.currency) {
        setCurrency(data.currency);
      }
    } catch (error) {
      console.error('Failed to load dashboard', error);
      message.error('Unable to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  useEffect(() => {
    const loadTasks = async () => {
      try {
        const tasksRes = await api.get('/api/v1/tasks/my/');
        const tasks = Array.isArray(tasksRes.data) ? tasksRes.data : tasksRes.data?.results || [];
        setMyTasks(tasks.slice(0, 5));
      } catch (e) {
        setMyTasks([]);
      }
    };
    loadTasks();
  }, []);

  const handleLayoutChange = (_layout, allLayouts) => {
    setLayouts(allLayouts);
  };

  const recordDashboardInterest = useCallback(() => {
    widgets.forEach((widget) => {
      const widgetId = widget.id || widget.key;
      if (!widgetId) {
        return;
      }
      trackMetadataInterest({
        kind: 'dashboard',
        entity: widgetId,
        widget_id: widgetId,
        widget_title: widget.title,
      }).catch(() => {});
    });
  }, [widgets]);

  const handlePublishDashboard = async () => {
  const defaultName = 'Dashboard ' + new Date().toLocaleDateString();
  const dashboardName = window.prompt('Name for dashboard definition', defaultName);
  if (!dashboardName) {
    message.info('Dashboard publish cancelled.');
    return;
  }
  const payload = {
    name: dashboardName,
    description: 'Saved from dashboard builder',
    layout: layouts,
    filters: { period },
    widgets: widgets.map((widget) => ({
      key: widget.id || widget.key,
      widget_type: widget.type,
      title: widget.title,
      config: { description: widget.description, size: widget.size, data: widget.data || null },
    })),
    scope_type: scopeType,
    layer: 'COMPANY_OVERRIDE',
    publish: publishNow,
  };
  message.loading({ content: 'Publishing dashboard...', key: 'dashboard-publish' });
  try {
    const { data } = await api.post('/api/v1/dashboard/definitions/', payload);
    message.success({ content: `Dashboard version ${data.version} stored.`, key: 'dashboard-publish' });
    recordDashboardInterest();
  } catch (error) {
    const detail = error?.response?.data?.detail || 'Unable to publish dashboard.';
    console.warn('Dashboard publish failed:', error?.message);
    message.error({ content: detail, key: 'dashboard-publish' });
  }
};

const handleSaveLayout = async () => {
  setSavingLayout(true);
  try {
    await api.put('/api/v1/dashboard/layout/', {
      layout: layouts,
      widgets: widgets.map((widget) => widget.id),
    });
    message.success('Dashboard layout saved.');
    recordDashboardInterest();
  } catch (error) {
    console.error('Failed to save layout', error);
    message.error('Could not save layout.');
  } finally {
    setSavingLayout(false);
  }
};

  

  const widgetCards = useMemo(
    () =>
      widgets.map((widget) => {
        const content = renderWidget(widget, currency);
        return (
          <div key={widget.id}>
            {content}
          </div>
        );
      }),
    [widgets, currency],
  );

  const currentLayouts = useMemo(() => layouts || defaultLayouts, [layouts]);

  return (
    <div>
      <PageHeader
        title="Command Center"
        subtitle="Visual overview of business performance"
        description="Drag widgets to personalize your workspace. Changes can be saved per user and company."
        extra={
          <Space size="middle" align="center">
            <Segmented options={PERIOD_OPTIONS} value={period} onChange={setPeriod} />
            <Space size="small">
              <Text type="secondary">Scope</Text>
              <Select
                size="small"
                value={scopeType}
                onChange={setScopeType}
                style={{ width: 150 }}
                options={[
                  { label: 'Company', value: 'COMPANY' },
                  { label: 'Company Group', value: 'GROUP' },
                  { label: 'Global', value: 'GLOBAL' },
                ]}
              />
            </Space>
            <Space size="small">
              <Switch checked={publishNow} onChange={setPublishNow} />
              <Text type="secondary">{publishNow ? 'Publish now' : 'Draft'}</Text>
            </Space>
            <Button icon={<SaveOutlined />} onClick={handlePublishDashboard}>
              Publish Dashboard
            </Button>
            <Button type="primary" onClick={handleSaveLayout} loading={savingLayout}>
              Save Layout
            </Button>
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={18}>
          {loading ? (
            <Spin tip="Loading dashboard" />
          ) : (
            <ResponsiveGridLayout
              className="draggable-dashboard"
              layouts={currentLayouts}
              breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
              cols={{ lg: 12, md: 12, sm: 12, xs: 6, xxs: 4 }}
              rowHeight={90}
              margin={[16, 16]}
              onLayoutChange={handleLayoutChange}
              draggableHandle=".drag-handle"
            >
              {widgetCards}
            </ResponsiveGridLayout>
          )}
        </Col>
        <Col xs={24} lg={6}>
          <Card title="My Tasks" bodyStyle={{ paddingTop: 8 }}>
            <List
              dataSource={myTasks}
              renderItem={(task) => (
                <List.Item key={task.id}>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Text strong ellipsis>
                      {task.title}
                    </Text>
                    <Text type="secondary">
                      {(task.status || '').replace('_', ' ')}{task.due_date ? ` · due ${new Date(task.due_date).toLocaleString()}` : ''}
                    </Text>
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

const renderWidget = (widget, currency) => {
  const { type, title, description, data, chartType } = widget;
  switch (type) {
    case 'kpi': {
      const icon = selectKpiIcon(widget.id);
      const trend = mapTrendPercentage(data?.trend || data?.series);
      const numericValue = data?.value ?? data?.total ?? 0;
      const isCurrency =
        widget.id.includes('revenue') ||
        widget.id.includes('receivables') ||
        widget.id.includes('payables');
      const displayValue = isCurrency ? formatCurrency(numericValue, currency) : formatNumber(numericValue);
      const suffix = !isCurrency ? widget.data?.suffix : undefined;
      return (
        <div className="drag-handle" style={{ height: '100%' }}>
          <StatCard
            title={title}
            value={displayValue}
            suffix={suffix}
            trend={trend}
            trendLabel="change"
            description={description}
            icon={icon}
          />
        </div>
      );
    }
    case 'chart': {
      const series = data?.series || [];
      const chartData =
        chartType === 'bar' ? buildCashflowDataset(series) : buildLineDataset(series, title, '#1677ff');
      const ChartComponent = chartType === 'bar' ? Bar : Line;
      return (
        <Card title={<span className="drag-handle">{title}</span>} extra={description} style={{ height: '100%' }}>
          <div style={{ height: '260px' }}>
            <ChartComponent
              data={chartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: true, position: 'bottom' },
                },
              }}
            />
          </div>
        </Card>
      );
    }
    case 'table': {
      const rows = data?.rows || [];
      const columns = [
        { title: 'Name', dataIndex: 'name', key: 'name' },
        {
          title: 'Total',
          dataIndex: 'total',
          key: 'total',
          render: (value) => formatCurrency(value, currency),
        },
      ];
      return (
        <div className="drag-handle" style={{ height: '100%' }}>
          <DataTable
            title={title}
            dataSource={rows.map((row, index) => ({ key: index, ...row }))}
            columns={columns}
            pagination={{ pageSize: 5 }}
          />
        </div>
      );
    }
    case 'list': {
      const items = data?.items || [];
      return (
        <Card
          title={<span className="drag-handle">{title}</span>}
          extra={description}
          bodyStyle={{ paddingTop: 0 }}
          style={{ height: '100%' }}
        >
          <List
            dataSource={items}
            renderItem={(item) => (
              <List.Item key={item.id || item.invoice_number || item.order_number}>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.order_number || item.invoice_number}</Text>
                      {item.status ? <Tag>{item.status}</Tag> : null}
                    </Space>
                  }
                  description={
                    <Space direction="vertical">
                      {item.customer ? <Text type="secondary">{item.customer}</Text> : null}
                      {item.due_date ? <Text type="secondary">Due {item.due_date}</Text> : null}
                    </Space>
                  }
                />
                <Text>{formatCurrency(item.total || item.balance, currency)}</Text>
              </List.Item>
            )}
          />
        </Card>
      );
    }
    default:
      return (
        <Card title={title}>
          <Text type="secondary">This widget type is not yet supported.</Text>
        </Card>
      );
  }
};

const selectKpiIcon = (widgetId) => {
  if (widgetId.includes('revenue')) {
    return <DollarOutlined style={{ color: '#389e0d' }} />;
  }
  if (widgetId.includes('orders')) {
    return <ShoppingCartOutlined style={{ color: '#1677ff' }} />;
  }
  if (widgetId.includes('receivables') || widgetId.includes('payables')) {
    return <AlertOutlined style={{ color: '#faad14' }} />;
  }
  return <RiseOutlined style={{ color: '#722ed1' }} />;
};

export default Dashboard;
