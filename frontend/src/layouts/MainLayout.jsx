import React, { useState, useEffect } from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, Space } from 'antd';
import {
  DashboardOutlined,
  DollarOutlined,
  ShoppingOutlined,
  TeamOutlined,
  ShopOutlined,
  SettingOutlined,
  BellOutlined,
  UserOutlined,
  LogoutOutlined,
  SwapOutlined,
  AppstoreOutlined,
  FormOutlined,
  BranchesOutlined,
  ProjectOutlined,
  ToolOutlined,
  PieChartOutlined,
  SolutionOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import CompanySelector from '../components/Common/CompanySelector';
import AIWidget from '../components/AIAssistant/AIWidget';
import logo from '../assets/twist_erp_logo.png';
import icon from '../assets/twist_erp_icon.png';

const { Header, Sider, Content, Footer } = Layout;

const MainLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [openKeys, setOpenKeys] = useState([]);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { currentCompany } = useCompany();

  useEffect(() => {
    const segments = location.pathname.split('/').filter(Boolean);
    if (segments.length) {
      setOpenKeys([segments[0]]);
    } else {
      setOpenKeys([]);
    }
  }, [location.pathname]);

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: 'finance',
      icon: <DollarOutlined />,
      label: 'Finance',
      children: [
        { key: '/finance', label: 'Finance Control Tower' },
        { key: '/finance/accounts', label: 'Chart of Accounts' },
        { key: '/finance/journals', label: 'Journal Vouchers' },
        { key: '/finance/invoices', label: 'Invoices' },
        { key: '/finance/payments', label: 'Payments' },
      ],
    },
    {
      key: 'inventory',
      icon: <AppstoreOutlined />,
      label: 'Inventory',
      children: [
        { key: '/inventory', label: 'Inventory Control Tower' },
        { key: '/inventory/products', label: 'Products' },
        { key: '/inventory/warehouses', label: 'Warehouses' },
        { key: '/inventory/movements', label: 'Stock Movements' },
      ],
    },
    {
      key: 'sales',
      icon: <ShoppingOutlined />,
      label: 'Sales & CRM',
      children: [
        { key: '/sales', label: 'Sales Control Tower' },
        { key: '/sales/customers', label: 'Customers' },
        { key: '/sales/orders', label: 'Sales Orders' },
        { key: '/sales/pipeline', label: 'Sales Pipeline' },
      ],
    },
    {
      key: 'procurement',
      icon: <ShopOutlined />,
      label: 'Procurement',
      children: [
        { key: '/procurement', label: 'Procurement Control Tower' },
        { key: '/procurement/suppliers', label: 'Suppliers' },
        { key: '/procurement/orders', label: 'Purchase Orders' },
      ],
    },
    {
      key: 'nocode',
      icon: <FormOutlined />,
      label: 'No-Code Tools',
      children: [
        { key: '/forms', label: 'Form Builder' },
        { key: '/workflows', label: 'Workflows' },
        { key: '/migration', label: 'Data Migration' },
      ],
    },
    {
      key: 'advanced',
      icon: <ProjectOutlined />,
      label: 'Advanced Modules',
      children: [
        {
          key: 'assets',
          icon: <ToolOutlined />,
          label: 'Asset Management',
          children: [
            { key: '/assets', label: 'Asset Command Center' },
            { key: '/assets/list', label: 'Asset Register' },
            { key: '/assets/maintenance', label: 'Maintenance Planner' },
          ],
        },
        {
          key: 'budgets',
          icon: <PieChartOutlined />,
          label: 'Budgeting',
          children: [
            { key: '/budgets', label: 'Budgeting Hub' },
            { key: '/budgets/list', label: 'Budget Registry' },
            { key: '/budgets/monitor', label: 'Budget Monitor' },
          ],
        },
        {
          key: 'production',
          icon: <ApartmentOutlined />,
          label: 'Production',
          children: [
            { key: '/production', label: 'Production Control Tower' },
            { key: '/production/boms', label: 'Bills of Materials' },
            { key: '/production/work-orders', label: 'Work Orders' },
          ],
        },
        {
          key: 'hr',
          icon: <SolutionOutlined />,
          label: 'HR & Payroll',
          children: [
            { key: '/hr', label: 'People Operations Hub' },
            { key: '/hr/employees', label: 'Employees' },
            { key: '/hr/attendance', label: 'Attendance' },
            { key: '/hr/payroll', label: 'Payroll Runs' },
          ],
        },
        {
          key: 'projects',
          icon: <ProjectOutlined />,
          label: 'Projects',
          children: [
            { key: '/projects', label: 'Projects Command Center' },
            { key: '/projects/list', label: 'Projects List' },
            { key: '/projects/gantt', label: 'Gantt Planner' },
          ],
        },
      ],
    },
  ];

  if (user?.is_system_admin || user?.is_staff) {
    menuItems.push({
      key: 'ai',
      icon: <RobotOutlined />,
      label: 'AI Ops',
      children: [{ key: '/ai/training-review', label: 'Training Review' }],
    });
  }

  const userDisplayName =
    user?.display_name ||
    [user?.first_name, user?.last_name].filter(Boolean).join(' ') ||
    user?.username ||
    'User';

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
      onClick: () => navigate('/settings/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: logout,
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        width={250}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px 0' }}>
          <img src={collapsed ? icon : logo} alt="Twist ERP Logo" style={{ height: '100%', maxWidth: '80%', objectFit: 'contain' }} />
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          openKeys={collapsed ? [] : openKeys}
          items={menuItems}
          onClick={handleMenuClick}
          onOpenChange={(keys) => setOpenKeys(keys)}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 250 }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'sticky',
            top: 0,
            zIndex: 100,
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <div>
            <CompanySelector />
          </div>
          <Space size="large">
            <Badge count={5}>
              <BellOutlined style={{ fontSize: 20 }} />
            </Badge>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>{userDisplayName}</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: '24px 16px', padding: 24, background: '#f0f2f5' }}>
          {children}
        </Content>
        <Footer style={{ textAlign: 'center' }}>
          TWIST ERP ©2025 Transform, Integrate, Simplify, Track
        </Footer>
        <AIWidget />
      </Layout>
    </Layout>
  );
};

export default MainLayout;
