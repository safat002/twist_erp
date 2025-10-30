import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useEdgesState,
  useNodesState,
} from 'react-flow-renderer';
import {
  Row,
  Col,
  Card,
  Space,
  Button,
  Select,
  Switch,
  Typography,
  List,
  Badge,
  Tabs,
  Tag,
  Timeline,
  message,
} from 'antd';
import {
  PlusOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  SaveOutlined,
  AimOutlined,
  RobotOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import api from '../../services/api';
import { useCompany } from '../../contexts/CompanyContext';

const { Title, Text } = Typography;

const fallbackFlow = {
  id: 'workflow-1',
  name: 'Supplier Onboarding Automation',
  description: 'Automated flow to evaluate, approve, and activate new suppliers.',
  nodes: [
    {
      id: 'trigger',
      data: { label: 'Trigger: Supplier Form Submitted' },
      position: { x: 80, y: 60 },
      style: { border: '2px solid #1890ff', padding: 12, borderRadius: 8, background: '#f0f5ff' },
    },
    {
      id: 'policy-check',
      data: { label: 'Policy Compliance Check' },
      position: { x: 320, y: 40 },
      style: { border: '2px solid #13c2c2', padding: 12, borderRadius: 8, background: '#e6fffb' },
    },
    {
      id: 'evaluation',
      data: { label: 'Risk Evaluation (AI)' },
      position: { x: 320, y: 160 },
      style: { border: '2px solid #722ed1', padding: 12, borderRadius: 8, background: '#f9f0ff' },
    },
    {
      id: 'approval',
      data: { label: 'Head of Procurement Approval' },
      position: { x: 580, y: 100 },
      style: { border: '2px solid #fa8c16', padding: 12, borderRadius: 8, background: '#fff7e6' },
    },
    {
      id: 'activate',
      data: { label: 'Activate Supplier & Notify Teams' },
      position: { x: 820, y: 100 },
      style: { border: '2px solid #52c41a', padding: 12, borderRadius: 8, background: '#f6ffed' },
    },
  ],
  edges: [
    { id: 'e1', source: 'trigger', target: 'policy-check', label: 'Run policy check' },
    { id: 'e2', source: 'trigger', target: 'evaluation', label: 'AI risk scoring' },
    { id: 'e3', source: 'policy-check', target: 'approval', label: 'If compliant' },
    { id: 'e4', source: 'evaluation', target: 'approval', label: 'Risk < threshold' },
    { id: 'e5', source: 'approval', target: 'activate', label: 'On approval' },
  ],
};

const fallbackRuns = [
  {
    id: 'run-1',
    status: 'Success',
    triggeredBy: 'Lamia Hasan',
    startedAt: '2024-06-12 09:30',
    duration: '00:03:21',
  },
  {
    id: 'run-2',
    status: 'Waiting Approval',
    triggeredBy: 'System (Form Submission)',
    startedAt: '2024-06-12 13:05',
    duration: '00:01:14',
  },
  {
    id: 'run-3',
    status: 'Failed',
    triggeredBy: 'Rahim Uddin',
    startedAt: '2024-06-11 15:42',
    duration: '00:02:45',
  },
];

const fallbackLibrary = [
  {
    id: 'lib-1',
    title: 'Overdue Invoice Reminder',
    description: 'Auto-send reminders, notify account managers, and schedule call tasks.',
    tags: ['Finance', 'Automation'],
  },
  {
    id: 'lib-2',
    title: 'Leave Approval Flow',
    description: 'Route requests to team leads, alert payroll, and update calendars.',
    tags: ['HR', 'Approvals'],
  },
  {
    id: 'lib-3',
    title: 'Quality Incident Escalation',
    description: 'Trigger NCR ticket, notify QA heads, and halt affected work orders.',
    tags: ['Manufacturing', 'Compliance'],
  },
];

const statusColor = {
  Success: 'green',
  'Waiting Approval': 'gold',
  Failed: 'red',
};

const WorkflowDesigner = () => {
  const { currentCompany } = useCompany();
  const [workflow, setWorkflow] = useState(fallbackFlow);
  const [runHistory, setRunHistory] = useState(fallbackRuns);
  const [library, setLibrary] = useState(fallbackLibrary);
  const [loading, setLoading] = useState(false);
  const [scopeType, setScopeType] = useState('COMPANY');
  const [publishNow, setPublishNow] = useState(true);

  const [nodes, setNodes, onNodesChange] = useNodesState(workflow.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(workflow.edges);

  useEffect(() => {
    const bootstrap = async () => {
      setLoading(true);
      try {
        if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
          setWorkflow(fallbackFlow);
          setNodes(fallbackFlow.nodes);
          setEdges(fallbackFlow.edges);
          setRunHistory(fallbackRuns);
          setLibrary(fallbackLibrary);
          return;
        }
        const response = await api.get('/api/v1/workflows/designer/', {
          params: { company: currentCompany.id },
        });
        const payload = response.data || {};
        if (payload.workflow) {
          setWorkflow(payload.workflow);
          setNodes(payload.workflow.nodes || []);
          setEdges(payload.workflow.edges || []);
        } else {
          setWorkflow(fallbackFlow);
          setNodes(fallbackFlow.nodes);
          setEdges(fallbackFlow.edges);
        }
        setRunHistory(Array.isArray(payload.run_history) ? payload.run_history : fallbackRuns);
        setLibrary(Array.isArray(payload.library) ? payload.library : fallbackLibrary);
      } catch (error) {
        console.warn('Workflow designer fallback data used:', error?.message);
        setWorkflow(fallbackFlow);
        setNodes(fallbackFlow.nodes);
        setEdges(fallbackFlow.edges);
        setRunHistory(fallbackRuns);
        setLibrary(fallbackLibrary);
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
  }, [currentCompany, setEdges, setNodes]);

  const onConnect = useCallback(
    (connection) =>
      setEdges((eds) => [
        ...eds,
        {
          ...connection,
          animated: true,
          style: { stroke: '#1890ff' },
        },
      ]),
    [setEdges],
  );

  const handlePublishTemplate = async () => {
    const payload = {
      name: workflow.name,
      description: workflow.description,
      definition: {
        nodes,
        edges,
      },
      scope_type: scopeType,
      layer: 'COMPANY_OVERRIDE',
      publish: publishNow,
    };
    message.loading({ content: 'Publishing workflow...', key: 'workflow-publish' });
    try {
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        message.info({ content: 'Demo company: workflow saved locally.', key: 'workflow-publish' });
        return;
      }
      const { data } = await api.post('/api/v1/workflows/templates/', payload);
      message.success({ content: `Workflow version ${data.version} stored.`, key: 'workflow-publish' });
    } catch (error) {
      const detail = error?.response?.data?.detail || 'Unable to publish workflow.';
      console.warn('Workflow publish failed:', error?.message);
      message.error({ content: detail, key: 'workflow-publish' });
    }
  };

  const handleRunWorkflow = async () => {
    message.loading({ content: 'Triggering workflow...', key: 'run' });
    try {
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        message.info({ content: 'Demo company: workflow simulated.', key: 'run' });
        return;
      }
      await api.post(`/api/v1/workflows/${workflow.id}/run/`);
      message.success({ content: 'Workflow started.', key: 'run' });
    } catch (error) {
      console.warn('Failed to run workflow:', error?.message);
      message.error({ content: 'Unable to trigger workflow.', key: 'run' });
    }
  };

  return (
    <div>
      <Title level={2}>Workflow Automation Studio</Title>
      <Text type="secondary">
        Design automation visually, orchestrate approvals, and monitor live executions across Twist ERP.
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={16}>
          <Card
            loading={loading}
            title={workflow.name}
            extra={
              <Space size="middle" align="center">
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
                <Button icon={<ThunderboltOutlined />}>Recommend Automations</Button>
                <Button icon={<SaveOutlined />} onClick={handlePublishTemplate}>
                  Publish
                </Button>
                <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleRunWorkflow}>
                  Run Flow
                </Button>
              </Space>
            }
            bodyStyle={{ height: 520, padding: 0 }}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              fitView
              nodesDraggable
              style={{ width: '100%', height: '100%' }}
            >
              <MiniMap zoomable pannable />
              <Controls showInteractive={false} />
              <Background gap={16} color="#e2e2e2" />
            </ReactFlow>
          </Card>
        </Col>

        <Col xs={24} md={8}>
          <Tabs
            defaultActiveKey="runs"
            items={[
              {
                key: 'runs',
                label: 'Run History',
                children: (
                  <List
                    dataSource={runHistory}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space direction="vertical" size={0} style={{ width: '100%' }}>
                          <Space align="baseline" style={{ justifyContent: 'space-between' }}>
                            <Text strong>{item.triggeredBy}</Text>
                            <Tag color={statusColor[item.status] || 'blue'}>{item.status}</Tag>
                          </Space>
                          <Text type="secondary">Started: {item.startedAt}</Text>
                          <Text type="secondary">Duration: {item.duration}</Text>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
              {
                key: 'library',
                label: 'Workflow Library',
                children: (
                  <List
                    dataSource={library}
                    renderItem={(item) => (
                      <List.Item key={item.id}>
                        <Space direction="vertical" size={0} style={{ width: '100%' }}>
                          <Space align="baseline" style={{ justifyContent: 'space-between' }}>
                            <Text strong>{item.title}</Text>
                            <Space>
                              {item.tags.map((tag) => (
                                <Tag key={tag} color="blue">
                                  {tag}
                                </Tag>
                              ))}
                            </Space>
                          </Space>
                          <Text type="secondary">{item.description}</Text>
                          <Button size="small" icon={<PlusOutlined />}>Clone to Workspace</Button>
                        </Space>
                      </List.Item>
                    )}
                  />
                ),
              },
            ]}
          />

          <Card title="Execution Insights" style={{ marginTop: 16 }}>
            <Timeline
              items={[
                {
                  color: 'green',
                  children: (
                    <Space>
                      <RobotOutlined style={{ color: '#52c41a' }} />
                      <Text>AI recommends adding vendor SLA monitoring branch.</Text>
                    </Space>
                  ),
                },
                {
                  color: 'blue',
                  children: (
                    <Space>
                      <AimOutlined style={{ color: '#1890ff' }} />
                      <Text>98% of runs complete within 3 minutes.</Text>
                    </Space>
                  ),
                },
                {
                  color: 'orange',
                  children: (
                    <Space>
                      <ApartmentOutlined style={{ color: '#faad14' }} />
                      <Text>Consider parallelizing policy check and risk evaluation.</Text>
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

export default WorkflowDesigner;

