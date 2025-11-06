import React from 'react';
import { Timeline, Tag } from 'antd';

const statusColor = (status) => {
  switch ((status || '').toLowerCase()) {
    case 'approved':
      return 'green';
    case 'rejected':
      return 'red';
    case 'sent_back':
      return 'orange';
    default:
      return 'blue';
  }
};

const labelFromType = (t) => (t === 'cost_center_owner' ? 'CC Owner' : 'Module Owner');

const ApprovalTimeline = ({ approvals = [] }) => (
  <Timeline mode="left">
    {approvals.map((a) => (
      <Timeline.Item color={statusColor(a.status)} key={a.id} label={new Date(a.created_at || a.decision_date).toLocaleString()}>
        <div>
          <strong>{labelFromType(a.approver_type)}</strong>{' '}
          <Tag color={statusColor(a.status)}>{a.status}</Tag>
        </div>
        {a.comments ? <div style={{ opacity: 0.8 }}>{a.comments}</div> : null}
      </Timeline.Item>
    ))}
  </Timeline>
);

export default ApprovalTimeline;

