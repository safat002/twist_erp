import React from 'react';
import { Layout, Breadcrumb, Space, Button, Typography, Row, Col, Divider } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Content } = Layout;
const { Title } = Typography;

/**
 * InventoryLayout - Unified layout wrapper for all inventory pages
 * Provides consistent header, breadcrumbs, actions, and content area
 */
const InventoryLayout = ({
  title,
  icon,
  breadcrumb = [],
  actions = [],
  children,
  subtitle,
  extra,
  contentPadding = 24,
  showDivider = true,
}) => {
  const navigate = useNavigate();

  // Build breadcrumb items
  const breadcrumbItems = [
    {
      title: (
        <span style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
          <HomeOutlined /> Home
        </span>
      ),
    },
    ...breadcrumb.map((item, index) => {
      if (typeof item === 'string') {
        return { title: item };
      }
      return {
        title: item.path ? (
          <span style={{ cursor: 'pointer' }} onClick={() => navigate(item.path)}>
            {item.label}
          </span>
        ) : (
          item.label
        ),
      };
    }),
  ];

  return (
    <Content style={{ padding: '0 24px', minHeight: 'calc(100vh - 112px)' }}>
      {/* Breadcrumb */}
      <Breadcrumb style={{ margin: '16px 0' }} items={breadcrumbItems} />

      {/* Page Header */}
      <div style={{ background: '#fff', padding: '24px', borderRadius: '8px', marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space align="start" size={16}>
              {icon && <div style={{ fontSize: 32, color: '#1890ff' }}>{icon}</div>}
              <div>
                <Title level={2} style={{ margin: 0 }}>
                  {title}
                </Title>
                {subtitle && (
                  <Typography.Text type="secondary" style={{ fontSize: 14 }}>
                    {subtitle}
                  </Typography.Text>
                )}
              </div>
            </Space>
          </Col>
          <Col>
            <Space size={8}>{actions}</Space>
          </Col>
        </Row>
        {extra && (
          <>
            <Divider style={{ margin: '16px 0' }} />
            {extra}
          </>
        )}
      </div>

      {/* Main Content */}
      <div
        style={{
          background: '#fff',
          padding: contentPadding,
          borderRadius: '8px',
          minHeight: 400,
        }}
      >
        {children}
      </div>
    </Content>
  );
};

export default InventoryLayout;
