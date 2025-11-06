import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Card, Row, Col, Table, Space, Button, Tag, Typography, message, Tabs, Modal, Input, Drawer, DatePicker, Select, Switch } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined, ArrowRightOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useCompany } from '../../contexts/CompanyContext';
import workflowService from '../../services/workflows';
import { listMigrationJobs, approveMigrationJob, rejectMigrationJob } from '../../services/dataMigration';

const { Title, Text } = Typography;

const MyApprovals = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [wfInstances, setWfInstances] = useState([]);
  const [migJobs, setMigJobs] = useState([]);
  const [rejectModal, setRejectModal] = useState({ open: false, id: null, notes: '' });
  const [detail, setDetail] = useState({ open: false, type: null, record: null });

  // Filters
  const [wfTemplateFilter, setWfTemplateFilter] = useState(null);
  const [wfDateRange, setWfDateRange] = useState([]);
  const [migEntityFilter, setMigEntityFilter] = useState(null);
  const [migDateRange, setMigDateRange] = useState([]);

  const [myQueueOnly, setMyQueueOnly] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [instances, jobs] = await Promise.all([
        workflowService.listInstances({ my_queue_only: myQueueOnly ? 1 : 0 }),
        listMigrationJobs(),
      ]);
      setWfInstances(instances || []);
      setMigJobs(jobs || []);
    } catch (err) {
      console.error(err);
      message.error('Failed to load approvals');
    } finally {
      setLoading(false);
    }
  }, [myQueueOnly]);

  useEffect(() => {
    if (currentCompany) load();
  }, [currentCompany, load]);

  const pendingWorkflows = useMemo(() => {
    let items = (wfInstances || []).filter(i => (i.state || '').toLowerCase() === 'submitted');
    if (wfTemplateFilter) items = items.filter(i => `${i.template?.id || ''}` === `${wfTemplateFilter}`);
    if (wfDateRange?.length === 2) {
      const [start, end] = wfDateRange;
      items = items.filter(i => {
        const t = new Date(i.updated_at);
        return (!start || t >= start.toDate()) && (!end || t <= end.toDate());
      });
    }
    return items;
  }, [wfInstances, wfTemplateFilter, wfDateRange]);

  const pendingMigrations = useMemo(() => {
    let items = (migJobs || []).filter(j => (j.status || '').toUpperCase() === 'AWAITING_APPROVAL');
    if (migEntityFilter) items = items.filter(j => (j.target_model || '').toLowerCase() === (migEntityFilter || '').toLowerCase());
    if (migDateRange?.length === 2) {
      const [start, end] = migDateRange;
      items = items.filter(j => {
        const t = new Date(j.submitted_for_approval_at || j.updated_at);
        return (!start || t >= start.toDate()) && (!end || t <= end.toDate());
      });
    }
    return items;
  }, [migJobs, migEntityFilter, migDateRange]);

  const wfColumns = [
    { title: 'Template', dataIndex: ['template', 'name'], key: 'template' },
    { title: 'State', dataIndex: 'state', key: 'state', render: v => <Tag color={v === 'submitted' ? 'orange' : 'default'}>{v}</Tag> },
    { title: 'Updated', dataIndex: 'updated_at', key: 'updated_at' },
    { title: 'Actions', key: 'actions', render: (_, record) => (
      <Space>
        <Button size='small' icon={<InfoCircleOutlined />} onClick={() => setDetail({ open: true, type: 'workflow', record })}>Details</Button>
        <Button size='small' icon={<ArrowRightOutlined />} onClick={async () => {
          try { await workflowService.transitionInstance(record.id, 'approved'); message.success('Approved'); load(); } catch (e) { message.error('Failed'); }
        }}>Approve</Button>
      </Space>
    ) },
  ];

  const migColumns = [
    { title: 'Job ID', dataIndex: 'id', key: 'id', width: 90 },
    { title: 'Entity', dataIndex: 'target_model', key: 'target_model' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: v => <Tag color='orange'>{v}</Tag> },
    { title: 'Submitted', dataIndex: 'submitted_for_approval_at', key: 'submitted_for_approval_at' },
    { title: 'Actions', key: 'actions', render: (_, record) => (
      <Space>
        <Button size='small' icon={<InfoCircleOutlined />} onClick={() => setDetail({ open: true, type: 'migration', record })}>Details</Button>
        <Button size='small' type='primary' icon={<CheckCircleOutlined />} onClick={async () => {
          try { await approveMigrationJob(record.id, { notes: 'Approved via My Approvals' }); message.success('Migration job approved'); load(); } catch (e) { message.error('Approve failed'); }
        }}>Approve</Button>
        <Button size='small' danger icon={<CloseCircleOutlined />} onClick={() => setRejectModal({ open: true, id: record.id, notes: '' })}>Reject</Button>
      </Space>
    ) },
  ];

  const handleReject = async () => {
    try {
      await rejectMigrationJob(rejectModal.id, { notes: rejectModal.notes || 'Rejected via My Approvals' });
      message.success('Migration job rejected');
      setRejectModal({ open: false, id: null, notes: '' });
      load();
    } catch (e) {
      message.error('Reject failed');
    }
  };

  return (
    <div>
      <Row justify='space-between' align='middle' style={{ marginBottom: 16 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 0 }}>My Approvals</Title>
          <Text type='secondary'>Workflows and migration approvals assigned to your company</Text>
        </Col>
        <Col>
          <Space>
            <span>
              <Text type='secondary' style={{ marginRight: 8 }}>My Queue Only</Text>
              <Switch size='small' checked={myQueueOnly} onChange={setMyQueueOnly} />
            </span>
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>Refresh</Button>
          </Space>
        </Col>
      </Row>
      <Tabs
        defaultActiveKey='workflows'
        items={[
          {
            key: 'workflows', label: `Workflows (${pendingWorkflows.length})`,
            children: (
              <Card title='Workflows Awaiting Approval' loading={loading}
                extra={(
                  <Space>
                    <DatePicker.RangePicker value={wfDateRange} onChange={setWfDateRange} allowEmpty={[true, true]} />
                    <Select
                      allowClear
                      placeholder='Filter by Template ID'
                      style={{ width: 200 }}
                      value={wfTemplateFilter}
                      onChange={setWfTemplateFilter}
                      options={(wfInstances||[]).map(i => ({ value: i.template?.id, label: `${i.template?.id} - ${i.template?.name}` }))}
                    />
                  </Space>
                )}
              >
                <Table columns={wfColumns} dataSource={pendingWorkflows} rowKey='id' size='small' pagination={{ pageSize: 8 }} />
              </Card>
            ),
          },
          {
            key: 'migration', label: `Data Migration (${pendingMigrations.length})`,
            children: (
              <Card title='Migration Jobs Awaiting Approval' loading={loading}
                extra={(
                  <Space>
                    <DatePicker.RangePicker value={migDateRange} onChange={setMigDateRange} allowEmpty={[true, true]} />
                    <Select
                      allowClear
                      placeholder='Filter by Entity'
                      style={{ width: 240 }}
                      value={migEntityFilter}
                      onChange={setMigEntityFilter}
                      options={[...new Set((migJobs||[]).map(j => j.target_model))].map(v => ({ value: v, label: v }))}
                    />
                  </Space>
                )}
              >
                <Table columns={migColumns} dataSource={pendingMigrations} rowKey='id' size='small' pagination={{ pageSize: 8 }} />
              </Card>
            ),
          },
        ]}
      />

      <Modal
        open={rejectModal.open}
        title='Reject Migration Job'
        okText='Reject'
        okButtonProps={{ danger: true }}
        onOk={handleReject}
        onCancel={() => setRejectModal({ open: false, id: null, notes: '' })}
      >
        <Text type='secondary'>Provide reason (optional)</Text>
        <Input.TextArea rows={3} value={rejectModal.notes} onChange={(e) => setRejectModal(prev => ({ ...prev, notes: e.target.value }))} />
      </Modal>

      <Drawer open={detail.open} width={520} onClose={() => setDetail({ open: false, type: null, record: null })} title='Approval Details'>
        {detail.type === 'workflow' && detail.record && (
          <Space direction='vertical' style={{ width: '100%' }}>
            <Card size='small' title='Workflow Instance'>
              <Space direction='vertical'>
                <Text><b>Template:</b> {detail.record.template?.name} (ID: {detail.record.template?.id})</Text>
                <Text><b>State:</b> <Tag>{detail.record.state}</Tag></Text>
                <Text type='secondary'>Updated: {detail.record.updated_at}</Text>
                <Space>
                  <Button type='primary' icon={<CheckCircleOutlined />} onClick={async () => { try { await workflowService.approveInstance(detail.record.id); message.success('Approved'); setDetail({ open: false, type: null, record: null }); load(); } catch (e) { message.error('Approve failed'); } }}>Approve</Button>
                </Space>
              </Space>
            </Card>
          </Space>
        )}
        {detail.type === 'migration' && detail.record && (
          <Space direction='vertical' style={{ width: '100%' }}>
            <Card size='small' title='Migration Job'>
              <Space direction='vertical'>
                <Text><b>Job ID:</b> {detail.record.id}</Text>
                <Text><b>Entity:</b> {detail.record.target_model}</Text>
                <Text><b>Status:</b> <Tag color='orange'>{detail.record.status}</Tag></Text>
                <Text type='secondary'>Submitted: {detail.record.submitted_for_approval_at}</Text>
                <Space>
                  <Button type='primary' icon={<CheckCircleOutlined />} onClick={async () => { try { await approveMigrationJob(detail.record.id, { notes: 'Approved via My Approvals' }); message.success('Approved'); setDetail({ open: false, type: null, record: null }); load(); } catch (e) { message.error('Approve failed'); } }}>Approve</Button>
                  <Button danger icon={<CloseCircleOutlined />} onClick={() => { setRejectModal({ open: true, id: detail.record.id, notes: '' }); setDetail({ open: false, type: null, record: null }); }}>Reject</Button>
                </Space>
              </Space>
            </Card>
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default MyApprovals;
