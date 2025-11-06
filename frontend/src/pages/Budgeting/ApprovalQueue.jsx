import React, { useEffect, useState } from 'react';
import { Card, Table, Space, Button, Modal, Input, message } from 'antd';
import { fetchApprovalQueue, approveCC, rejectCC, approveFinal, rejectFinal, fetchBudgetLines, updateBudgetLine } from '../../services/budget';

const ApprovalQueue = () => {
  const [loading, setLoading] = useState(true);
  const [queue, setQueue] = useState([]);
  const [comment, setComment] = useState('');
  const [processingId, setProcessingId] = useState(null);
  const [modifyOpen, setModifyOpen] = useState(false);
  const [modifyLines, setModifyLines] = useState([]);
  const [modifyBudgetId, setModifyBudgetId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await fetchApprovalQueue();
      setQueue(Array.isArray(data) ? data : data?.results || []);
    } catch (e) {
      message.error('Failed to load approval queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const doAction = async (record, actionFn) => {
    setProcessingId(record.id);
    try {
      await actionFn(record.budget_id, { comments: comment });
      setComment('');
      message.success('Action completed');
      load();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed');
    } finally {
      setProcessingId(null);
    }
  };

  const openModifyApprove = async (record) => {
    try {
      const { data } = await fetchBudgetLines({ budget: record.budget_id, page_size: 500 });
      const rows = data?.results || data || [];
      setModifyLines(rows.map((r) => ({ ...r, _new_qty: r.qty_limit, _new_value: r.value_limit, _reason: '' })));
      setModifyBudgetId(record.budget_id);
      setModifyOpen(true);
    } catch (e) {
      message.error('Failed to load lines');
    }
  };

  const columns = [
    { title: 'Budget', dataIndex: 'budget_name' },
    { title: 'Type', dataIndex: 'approver_type' },
    { title: 'Cost Center', dataIndex: 'cost_center' },
    {
      title: 'Actions',
      render: (_, r) => (
        <Space>
          {r.approver_type === 'cost_center_owner' ? (
            <>
              <Button size="small" type="primary" loading={processingId === r.id} onClick={() => openModifyApprove(r)}>
                Modify & Approve
              </Button>
              <Button size="small" danger loading={processingId === r.id} onClick={() => doAction(r, rejectCC)}>
                Send Back
              </Button>
            </>
          ) : (
            <>
              <Button size="small" type="primary" loading={processingId === r.id} onClick={() => doAction(r, approveFinal)}>
                Approve Final
              </Button>
              <Button size="small" danger loading={processingId === r.id} onClick={() => doAction(r, rejectFinal)}>
                Send Back
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card title="My Approval Queue" extra={<Input.TextArea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comments..." rows={1} style={{ width: 320 }} />}>
        <Table rowKey="id" loading={loading} dataSource={queue} columns={columns} />
      </Card>
      <Modal
        title="Modify Lines & Approve"
        open={modifyOpen}
        width={920}
        okText="Save Changes & Approve"
        onCancel={() => { setModifyOpen(false); setModifyLines([]); setModifyBudgetId(null); }}
        onOk={async () => {
          try {
            const diff = modifyLines.filter((r) => r._new_qty !== r.qty_limit || r._new_value !== r.value_limit || (r._reason || '').length);
            await Promise.all(diff.map((r) => updateBudgetLine(r.id, { qty_limit: r._new_qty, value_limit: r._new_value, modification_reason: r._reason })));
            await approveCC(modifyBudgetId, { comments: comment });
            message.success('Approved with modifications');
            setModifyOpen(false);
            setModifyLines([]);
            setModifyBudgetId(null);
            setComment('');
            load();
          } catch (e) {
            message.error(e?.response?.data?.detail || 'Failed to approve with modifications');
          }
        }}
      >
        <Table
          rowKey="id"
          dataSource={modifyLines}
          pagination={{ pageSize: 8 }}
          columns={[
            { title: 'Item', dataIndex: 'item_name' },
            { title: 'Qty', render: (_, r) => <Input type="number" value={r._new_qty} onChange={(e) => setModifyLines((prev) => prev.map((x) => x.id === r.id ? { ...x, _new_qty: Number(e.target.value) } : x))} style={{ width: 100 }} /> },
            { title: 'Value', render: (_, r) => <Input type="number" value={r._new_value} onChange={(e) => setModifyLines((prev) => prev.map((x) => x.id === r.id ? { ...x, _new_value: Number(e.target.value) } : x))} style={{ width: 140 }} /> },
            { title: 'Reason', render: (_, r) => <Input value={r._reason} onChange={(e) => setModifyLines((prev) => prev.map((x) => x.id === r.id ? { ...x, _reason: e.target.value } : x))} /> },
          ]}
        />
      </Modal>
    </>
  );
};

export default ApprovalQueue;
