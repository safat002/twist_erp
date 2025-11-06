import React, { useMemo } from 'react';
import { Button, Dropdown, Space, Typography, Avatar, Tooltip, Skeleton } from 'antd';
import {
  ApartmentOutlined,
  CheckOutlined,
  ReloadOutlined,
  SettingOutlined,
  GlobalOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useCompany } from '../../contexts/CompanyContext';

const CompanySelector = () => {
  const navigate = useNavigate();
  const {
    companies,
    currentCompany,
    loading,
    switchCompany,
    refreshCompanies,
    error,
  } = useCompany();

  const companyMenuItems = useMemo(() => {
    if (!companies.length) {
      return [
        {
          key: 'empty',
          disabled: true,
          label: (
            <Space direction="vertical" size={0}>
              <Typography.Text strong>No companies yet</Typography.Text>
              <Typography.Text type="secondary">
                Create one to start tracking multi-entity data.
              </Typography.Text>
            </Space>
          ),
        },
      ];
    }

    return companies.map((company) => ({
      key: String(company.id),
      label: (
        <Space align="start">
          <Avatar
            size="small"
            style={{
              backgroundColor:
                company.id === currentCompany?.id ? 'var(--ant-color-primary)' : '#d9d9d9',
            }}
          >
            {(company.code || company.name || '?')
              .toString()
              .slice(0, 2)
              .toUpperCase()}
          </Avatar>
          <Space direction="vertical" size={0}>
            <Typography.Text strong>{company.name}</Typography.Text>
            <Typography.Text type="secondary">
              {(company.code || '').toString().toUpperCase()} - {company.industry || 'Business'}
            </Typography.Text>
          </Space>
        </Space>
      ),
      icon: company.id === currentCompany?.id ? <CheckOutlined /> : <ApartmentOutlined />,
    }));
  }, [companies, currentCompany?.id]);

  const menuItems = useMemo(() => {
    const baseItems = [...companyMenuItems];

    if (baseItems.length) {
      baseItems.push({ type: 'divider' });
    }

    baseItems.push({
      key: 'refresh',
      label: 'Refresh company list',
      icon: <ReloadOutlined />,
    });

    return baseItems;
  }, [companyMenuItems]);

  const handleMenuClick = ({ key }) => {
    if (key === 'refresh') {
      refreshCompanies();
      return;
    }
    // 'manage' action intentionally hidden from navbar
    switchCompany(key);
  };

  if (loading && !currentCompany) {
    return <Skeleton.Button active size="small" style={{ width: 200 }} />;
  }

  const label = currentCompany ? (
    <Space direction="vertical" size={0} align="start">
      <Typography.Text strong ellipsis style={{ maxWidth: 180 }}>
        {currentCompany.name}
      </Typography.Text>
      <Typography.Text type="secondary" ellipsis style={{ maxWidth: 180 }}>
        {(currentCompany.code || '').toString().toUpperCase()} - {currentCompany.timezone || currentCompany.industry || 'Multi-company ready'}
      </Typography.Text>
    </Space>
  ) : (
    <Typography.Text>Select company</Typography.Text>
  );

  return (
    <Dropdown
      menu={{
        items: menuItems,
        onClick: handleMenuClick,
      }}
      trigger={['click']}
      overlayStyle={{ width: 320 }}
    >
      <Button
        type="text"
        icon={
          loading ? (
            <LoadingOutlined />
          ) : (
            <Tooltip
              title={
                error
                  ? 'Company service unavailable, using demo data'
                  : 'Switch between entities'
              }
            >
              <GlobalOutlined />
            </Tooltip>
          )
        }
        style={{
          padding: '0 12px',
          height: 48,
          display: 'flex',
          alignItems: 'center',
          borderRadius: 10,
          border: '1px solid var(--ant-color-border)',
          background:
            currentCompany && !loading ? 'rgba(24, 144, 255, 0.06)' : 'rgba(0,0,0,0.02)',
        }}
      >
        <Space align="center">
          <Avatar
            style={{ backgroundColor: '#1890ff' }}
            size={32}
            icon={<ApartmentOutlined />}
          />
          {label}
        </Space>
      </Button>
    </Dropdown>
  );
};

export default CompanySelector;

