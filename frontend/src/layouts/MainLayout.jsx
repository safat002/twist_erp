import React, { useState, useEffect } from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, Space, List, Typography, Modal, Form, Input, DatePicker, Button, Select } from 'antd';
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
  ApartmentOutlined,
  FormOutlined,
  BranchesOutlined,
  ProjectOutlined,
  ToolOutlined,
  PieChartOutlined,
  SolutionOutlined,
  RobotOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../services/api';
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
  const { user, logout, isAuthenticated } = useAuth();
  const { currentCompany } = useCompany();
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [createVisible, setCreateVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    const segments = location.pathname.split('/').filter(Boolean);
    if (segments.length) {
      setOpenKeys([segments[0]]);
    } else {
      setOpenKeys([]);
    }
  }, [location.pathname]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      if (!isAuthenticated) return;
      try {
        const { data } = await api.get('/api/v1/notifications/');
        if (!mounted) return;
        const list = Array.isArray(data) ? data : data?.results || [];
        setNotifications(list);
        const unread = list.filter((n) => (n.status || 'unread') === 'unread').length;
        setUnreadCount(unread);
      } catch (err) {
        // silent fail
      }
    };
    load();
    const id = setInterval(load, 60000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [currentCompany?.id, isAuthenticated]);

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: 'workboard',
      icon: <SolutionOutlined />,
      label: 'Workboard',
      children: [
        { key: '/tasks', label: 'My Tasks' },
        { key: '/tasks/team', label: 'Team Tasks' },
        { key: '/notifications', label: 'Notification Center' },
      ],
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
        { key: '/reports', label: 'Report Builder' },
        { key: '/workflows', label: 'Workflows' },
        { key: '/migration', label: 'Data Migration' },
      ],
    },
    {
      key: 'company',
      icon: <ApartmentOutlined />,
      label: 'Company',
      children: [
        { key: '/company-management', label: 'Company Management' },
      ],
    },
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
      label: 'Cost Centers & Budgeting',
      children: [
        { key: '/budgets', label: 'Budgeting Hub' },
        { key: '/budgets/cost-centers', label: 'Cost Centers' },
        { key: '/budgets/item-codes', label: 'Item Codes' },
        { key: '/budgets/uoms', label: 'Units of Measure' },
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
        { key: '/hr/leave', label: 'Leave Management' },
        { key: '/hr/advances-loans', label: 'Advances & Loans' },
        { key: '/hr/recruitment', label: 'Recruitment' },
        { key: '/hr/onboarding', label: 'Onboarding' },
        { key: '/hr/performance', label: 'Performance' },
        { key: '/hr/exit-management', label: 'Exit Management' },
        { key: '/hr/policies', label: 'Policy Management' },
        { key: '/hr/attendance', label: 'Attendance' },
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

  const notifItems = (notifications || []).slice(0, 10).map((n) => ({
    key: String(n.id),
    label: (
      <div style={{ maxWidth: 360 }}>
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Typography.Text strong ellipsis>{n.title}</Typography.Text>
          {n.body ? (
            <Typography.Text type="secondary" ellipsis>
              {n.body}
            </Typography.Text>
          ) : null}
          {(n.status || 'unread') === 'unread' ? (
            <Button type="link" size="small" style={{ padding: 0 }} onClick={(e) => { e.domEvent?.stopPropagation?.(); }}>
              {/* placeholder to prevent collapse on click */}
            </Button>
          ) : null}
        </Space>
      </div>
    ),
  }));
  const notifMenu = {
    items: [
      ...notifItems,
      { type: 'divider' },
      { key: '__mark_all', label: 'Mark all read' },
      { key: '__view_all', label: 'View all notifications' },
    ],
    onClick: async ({ key }) => {
      if (key === '__view_all') {
        setNotifOpen(false);
        navigate('/notifications');
        return;
      }
      if (key === '__mark_all') {
        try {
          await Promise.all((notifications || []).filter((n) => (n.status || 'unread') === 'unread').map((n) => api.patch(`/api/v1/notifications/${n.id}/mark/`, { status: 'read' })));
          setNotifications((prev) => prev.map((n) => ({ ...n, status: 'read' })));
          setUnreadCount(0);
        } catch (e) {}
        return;
      }
      // item click marks read
      const id = Number(key);
      if (!Number.isNaN(id)) {
        try {
          await api.patch(`/api/v1/notifications/${id}/mark/`, { status: 'read' });
          setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, status: 'read' } : n)));
          const unread = notifications.filter((n) => n.id !== id && (n.status || 'unread') === 'unread').length;
          setUnreadCount(unread);
        } catch (e) {}
      }
    },
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
            <Dropdown
              menu={notifMenu}
              placement="bottomRight"
              trigger={["click"]}
              onOpenChange={setNotifOpen}
              open={notifOpen}
            >
              <Badge count={unreadCount} overflowCount={99} offset={[0, 4]}>
                <BellOutlined style={{ fontSize: 20, cursor: 'pointer' }} onClick={() => setNotifOpen((v) => !v)} />
              </Badge>
            </Dropdown>
            <Button size="small" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)} disabled={!user}>
              New Task
            </Button>
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
        <Modal
          title="Create Task"
          open={createVisible}
          onCancel={() => setCreateVisible(false)}
          onOk={async () => {
            try {
              const values = await form.validateFields();
              setCreating(true);
              await api.post('/api/v1/tasks/', {
                task_type: 'personal',
                title: values.title,
                description: values.description || '',
                due_date: values.due_date ? values.due_date.toISOString() : null,
                assigned_to: user?.id,
                priority: values.priority || 'normal',
                visibility_scope: 'private',
                recurrence: values.recurrence || 'none',
                recurrence_until: values.recurrence_until ? values.recurrence_until.toISOString() : null,
              });
              setCreateVisible(false);
              form.resetFields();
            } catch (e) {
              // noop
            } finally {
              setCreating(false);
            }
          }}
          confirmLoading={creating}
        >
          <Form layout="vertical" form={form}>
            <Form.Item name="title" label="Title" rules={[{ required: true, message: 'Please input a title' }]}>
              <Input placeholder="Task title" />
            </Form.Item>
            <Form.Item name="description" label="Description">
              <Input.TextArea rows={3} placeholder="Optional details" />
            </Form.Item>
            <Form.Item name="due_date" label="Due Date">
              <DatePicker showTime style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="priority" label="Priority" initialValue="normal">
              <Select
                options={[
                  { value: 'low', label: 'Low' },
                  { value: 'normal', label: 'Normal' },
                  { value: 'high', label: 'High' },
                  { value: 'critical', label: 'Critical' },
                ]}
              />
            </Form.Item>
            <Form.Item name="recurrence" label="Repeat" initialValue="none">
              <Select
                options={[
                  { value: 'none', label: 'Does not repeat' },
                  { value: 'daily', label: 'Daily' },
                  { value: 'weekly', label: 'Weekly' },
                  { value: 'monthly', label: 'Monthly' },
                ]}
              />
            </Form.Item>
            <Form.Item name="recurrence_until" label="Repeat Until">
              <DatePicker showTime style={{ width: '100%' }} />
            </Form.Item>
          </Form>
        </Modal>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
