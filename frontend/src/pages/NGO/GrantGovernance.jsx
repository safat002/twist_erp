import React from 'react';
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

const GrantGovernance = () => {
  return (
    <div>
      <Title level={2}>Grant Governance</Title>
      <Paragraph type="secondary">
        Manage grants, donors, disbursements, and compliance workflows.
      </Paragraph>
      <Card>
        <Paragraph>
          This area will centralize grant lifecycle management. Configure donors, programs,
          define budget lines, and track utilization with audit-friendly trails.
        </Paragraph>
      </Card>
    </div>
  );
};

export default GrantGovernance;

