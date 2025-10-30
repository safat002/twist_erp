import React, { useEffect, useState } from 'react';
import { Button, Card, Space, Table, Tag, Tabs, Modal, Input, message } from 'antd';
import {
  fetchAITrainingExamples,
  updateAITrainingExample,
  fetchLoRARuns,
  triggerLoRARun,
  bulkUpdateAITrainingExamples,
} from '../../services/ai';

const statusColors = {
  review: 'gold',
  approved: 'green',
  rejected: 'red',
};

const runStatusColors = {
  queued: 'gold',
  running: 'blue',
  success: 'green',
  failed: 'red',
};

const AiTrainingReview = () => {
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('review');
  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('queue');
  const [triggeringRun, setTriggeringRun] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [noteModal, setNoteModal] = useState({
    open: false,
    ids: [],
    status: 'approved',
    notes: '',
  });
  const [noteSubmitting, setNoteSubmitting] = useState(false);

  useEffect(() => {
    loadExamples(statusFilter);
  }, [statusFilter]);

  useEffect(() => {
    if (activeTab === 'runs') {
      loadRuns();
    }
  }, [activeTab]);

  const loadExamples = async (status) => {
    setLoading(true);
    try {
      const { data } = await fetchAITrainingExamples({ status });
      setSelectedRowKeys([]);
      setExamples(data.results || []);
    } catch (error) {
      message.error('Unable to load training examples');
    } finally {
      setLoading(false);
    }
  };

  const loadRuns = async () => {
    setRunsLoading(true);
    try {
      const { data } = await fetchLoRARuns({ limit: 25 });
      setRuns(data.results || []);
    } catch (error) {
      message.error('Unable to load LoRA run history');
    } finally {
      setRunsLoading(false);
    }
  };

  const handleTriggerRun = async () => {
    setTriggeringRun(true);
    try {
      await triggerLoRARun();
      message.success('Queued LoRA training run');
      loadRuns();
    } catch (error) {
      message.error('Unable to trigger LoRA job');
    } finally {
      setTriggeringRun(false);
    }
  };

  const openNoteModal = ({ ids, status, notes = '' }) => {
    setNoteModal({ open: true, ids, status, notes });
  };

  const handleModalCancel = () => {
    setNoteModal((prev) => ({ ...prev, open: false }));
  };

  const handleModalSubmit = async () => {
    if (!noteModal.ids.length) {
      return;
    }
    setNoteSubmitting(true);
    const payload = { status: noteModal.status, notes: noteModal.notes };
    try {
      if (noteModal.ids.length > 1) {
        await bulkUpdateAITrainingExamples({ ids: noteModal.ids, ...payload });
        message.success(`Updated ${noteModal.ids.length} examples`);
      } else {
        await updateAITrainingExample({ id: noteModal.ids[0], ...payload });
        message.success(`Marked example as ${noteModal.status}`);
      }
      setNoteModal({ open: false, ids: [], status: 'approved', notes: '' });
      setSelectedRowKeys([]);
      loadExamples(statusFilter);
    } catch (error) {
      message.error('Failed to update training examples');
    } finally {
      setNoteSubmitting(false);
    }
  };

  const handleUpdate = (example, status) => {
    openNoteModal({ ids: [example.id], status, notes: example.review_notes || '' });
  };

  const columns = [
    {
      title: 'Source',
      dataIndex: ['source'],
      key: 'source',
      render: (value) => <Tag>{value}</Tag>,
      width: 120,
    },
    {
      title: 'Prompt',
      dataIndex: 'prompt',
      key: 'prompt',
      ellipsis: true,
    },
    {
      title: 'Completion',
      dataIndex: 'completion',
      key: 'completion',
      ellipsis: true,
    },
    {
      title: 'Company',
      dataIndex: 'company',
      key: 'company',
      render: (company) => company?.code || 'Global',
      width: 120,
    },
    {
      title: 'Reviewer Notes',
      dataIndex: 'review_notes',
      key: 'review_notes',
      width: 220,
      ellipsis: true,
      render: (value) => value || 'â€”',
    },
    {
      title: 'Reviewed By',
      dataIndex: 'reviewed_by',
      key: 'reviewed_by',
      width: 180,
      render: (user) => user?.name || 'â€”',
    },
    {
      title: 'Reviewed At',
      dataIndex: 'reviewed_at',
      key: 'reviewed_at',
      width: 200,
      render: (value) => (value ? new Date(value).toLocaleString() : '—'),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => <Tag color={statusColors[status] || 'default'}>{status}</Tag>,
      width: 120,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type="primary"
            onClick={() => handleUpdate(record, 'approved')}
          >
            Approve
          </Button>
          <Button
            size="small"
            danger
            onClick={() => handleUpdate(record, 'rejected')}
          >
            Reject
          </Button>
        </Space>
      ),
    },
  ];

  const runColumns = [
    {
      title: 'Run ID',
      dataIndex: 'run_id',
      key: 'run_id',
      width: 200,
      render: (value) => value.slice(0, 8),
    },
    {
      title: 'Adapter',
      dataIndex: 'adapter_type',
      key: 'adapter_type',
      width: 120,
      render: (value) => value?.toUpperCase(),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value) => <Tag color={runStatusColors[value] || 'default'}>{value}</Tag>,
    },
    {
      title: 'Dataset Size',
      dataIndex: 'dataset_size',
      key: 'dataset_size',
      width: 140,
      render: (value) => (value ? value : 'â€”'),
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 200,
      render: (value) => (value ? new Date(value).toLocaleString() : '—'),
    },
    {
      title: 'Finished',
      dataIndex: 'finished_at',
      key: 'finished_at',
      width: 200,
      render: (value) => (value ? new Date(value).toLocaleString() : '—'),
    },
    {
      title: 'Triggered By',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
      render: (user) => user?.name || 'System',
      width: 180,
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: setSelectedRowKeys,
  };

  const hasSelection = selectedRowKeys.length > 0;

  return (
    <Card
      title="AI Ops Training Workspace"
      extra={
        activeTab === 'queue' ? (
          <Space>
            <Button
              type={statusFilter === 'review' ? 'primary' : 'default'}
              onClick={() => setStatusFilter('review')}
            >
              Pending
            </Button>
            <Button
              type={statusFilter === 'approved' ? 'primary' : 'default'}
              onClick={() => setStatusFilter('approved')}
            >
              Approved
            </Button>
            <Button
              type={statusFilter === 'rejected' ? 'primary' : 'default'}
              onClick={() => setStatusFilter('rejected')}
            >
              Rejected
            </Button>
          </Space>
        ) : (
          <Space>
            <Button
              type="primary"
              loading={triggeringRun}
              onClick={handleTriggerRun}
            >
              Trigger LoRA Run
            </Button>
          </Space>
        )
      }
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Training Queue" key="queue">
          <Space style={{ marginBottom: 16 }} wrap>
            <Button
              type="primary"
              size="small"
              disabled={!hasSelection}
              onClick={() => openNoteModal({ ids: selectedRowKeys, status: 'approved' })}
            >
              Bulk Approve
            </Button>
            <Button
              danger
              size="small"
              disabled={!hasSelection}
              onClick={() => openNoteModal({ ids: selectedRowKeys, status: 'rejected' })}
            >
              Bulk Reject
            </Button>
            {hasSelection && (
              <Button size="small" onClick={() => setSelectedRowKeys([])}>
                Clear Selection
              </Button>
            )}
          </Space>
          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={examples}
            rowSelection={rowSelection}
            pagination={{ pageSize: 10 }}
          />
        </Tabs.TabPane>
        <Tabs.TabPane tab="LoRA Run History" key="runs">
          <Table
            rowKey="run_id"
            loading={runsLoading}
            columns={runColumns}
            dataSource={runs}
            pagination={{ pageSize: 10 }}
          />
        </Tabs.TabPane>
      </Tabs>
      <Modal
        title={`Reviewer Notes (${noteModal.status})`}
        open={noteModal.open}
        onCancel={handleModalCancel}
        onOk={handleModalSubmit}
        confirmLoading={noteSubmitting}
        okText="Save"
      >
        <Input.TextArea
          rows={4}
          value={noteModal.notes}
          onChange={(event) => setNoteModal((prev) => ({ ...prev, notes: event.target.value }))}
          placeholder="Add optional reviewer notes"
        />
        {noteModal.ids.length > 1 && (
          <div style={{ marginTop: 8, color: '#888' }}>
            Applying to {noteModal.ids.length} examples.
          </div>
        )}
      </Modal>
    </Card>
  );
};

export default AiTrainingReview;
