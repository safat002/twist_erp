import React from 'react';
import { Space, Typography } from 'antd';

const { Title, Text } = Typography;

const containerStyle = {
  marginBottom: 24,
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 16,
};

const PageHeader = ({ title, subtitle, description, extra }) => (
  <div style={containerStyle}>
    <Space direction="vertical" size={4}>
      <Title level={2} style={{ margin: 0 }}>
        {title}
      </Title>
      {subtitle ? (
        <Text type="secondary">
          {subtitle}
        </Text>
      ) : null}
      {description ? (
        <Text type="secondary">
          {description}
        </Text>
      ) : null}
    </Space>
    {extra ? <Space>{extra}</Space> : null}
  </div>
);

export default PageHeader;
