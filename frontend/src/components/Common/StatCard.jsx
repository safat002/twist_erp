import React from 'react';
import { Card, Space, Typography } from 'antd';

const { Text, Title } = Typography;

const StatCard = ({
  title,
  value,
  suffix,
  trend,
  description,
  icon,
  trendLabel,
  loading,
}) => (
  <Card loading={loading}>
    <Space direction="vertical" size={4} style={{ width: '100%' }}>
      <Space align="center" size={8}>
        {icon}
        <Text type="secondary">{title}</Text>
      </Space>
      <Title level={3} style={{ margin: 0 }}>
        {value}
        {suffix ? (
          <Text type="secondary" style={{ marginLeft: 6 }}>
            {suffix}
          </Text>
        ) : null}
      </Title>
      {trend ? (
        <Text type={trend >= 0 ? 'success' : 'danger'}>
          {trend >= 0 ? '+' : ''}
          {trend}%
          {trendLabel ? ` ${trendLabel}` : ''}
        </Text>
      ) : null}
      {description ? <Text type="secondary">{description}</Text> : null}
    </Space>
  </Card>
);

export default StatCard;
