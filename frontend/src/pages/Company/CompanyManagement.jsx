import React, { useState, useEffect } from 'react';
import { Card, Typography, Table, Button, Tabs } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useCompany } from '../../contexts/CompanyContext';
import FeatureToggleManager from './FeatureToggleManager'; // Assuming this component will be created

const { Title } = Typography;
const { TabPane } = Tabs;

const CompanyManagement = () => {
  const { companies, loading, refreshCompanies } = useCompany();
  // Editing/provisioning of companies is disabled per requirement

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Currency', dataIndex: 'currency_code', key: 'currency_code' },
  ];

  return (
    <>
      <Title level={2}>Company Management</Title>
      <Tabs defaultActiveKey="1">
        <TabPane tab="Companies" key="1">
          <Card>
        <div style={{ marginBottom: 16 }}>
          <Button icon={<ReloadOutlined />} onClick={refreshCompanies} loading={loading}>
            Refresh
          </Button>
        </div>
            <Table columns={columns} dataSource={companies} rowKey="id" loading={loading} />
          </Card>
        </TabPane>
        <TabPane tab="Feature Management" key="2">
          <FeatureToggleManager />
        </TabPane>
      </Tabs>

      {/* No company edit/provision form by design */}
    </>
  );
};

export default CompanyManagement;
