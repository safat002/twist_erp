import React, { useState, useEffect, useMemo } from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, Space, List, Typography, Modal, Form, Input, DatePicker, Button, Select, Tag, message } from 'antd';
import dayjs from 'dayjs';
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
  SafetyCertificateOutlined,
  HeartOutlined,
  MoneyCollectOutlined,
  BankOutlined,
  AuditOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useCompany } from '../contexts/CompanyContext';
import { useFeatures } from '../contexts/FeatureContext';
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
  const { isFeatureEnabled, getFeature, refreshFeatures } = useFeatures();
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
        const { data } = await api.get('/api/v1/notifications/?limit=10');
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

  const iconFromFeature = (moduleKey, featureKey = 'module') => {
    try {
      const f = getFeature(moduleKey, featureKey);
      const icon = (f?.icon || '').toString();
      if (!icon) return null;
      if (icon.includes('shield')) return <SafetyCertificateOutlined />; // mdi-shield-check
      if (icon.includes('hand-coin')) return <AuditOutlined />; // mdi-hand-coin (approx)
      if (icon.includes('cash') || icon.includes('currency')) return <MoneyCollectOutlined />; // mdi-cash-multiple
      if (icon.includes('bank')) return <BankOutlined />; // mdi-bank
      if (icon.includes('hand-heart') || icon.includes('heart')) return <HeartOutlined />; // mdi-hand-heart
      if (icon.includes('robot')) return <RobotOutlined />; // mdi-robot
      return null;
    } catch (_) {
      return null;
    }
  };

  const menuItems = [
    {
      key: '/',
      icon: iconFromFeature('dashboard') || <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: 'workboard',
      icon: iconFromFeature('tasks') || <SolutionOutlined />,
      label: 'Workboard',
      children: [
        { key: '/tasks', label: 'My Tasks', icon: iconFromFeature('tasks') },
        { key: '/tasks/team', label: 'Team Tasks', icon: iconFromFeature('tasks') },
        { key: '/notifications', label: 'Notification Center', icon: iconFromFeature('notifications') },
        { key: '/approvals', label: 'My Approvals' },
      ],
    },
    {
      key: 'finance',
      icon: iconFromFeature('finance') || <DollarOutlined />,
      label: 'Finance',
      children: [
        { key: '/finance', label: 'Finance Control Tower', icon: iconFromFeature('finance') },
        { key: '/finance/accounts', label: 'Chart of Accounts', icon: iconFromFeature('finance', 'chart_of_accounts') },
        { key: '/finance/journals', label: 'Journal Vouchers', icon: iconFromFeature('finance', 'journal_vouchers') },
        { key: '/finance/invoices', label: 'Invoices', icon: iconFromFeature('finance', 'invoices') },
        { key: '/finance/payments', label: 'Payments', icon: iconFromFeature('finance', 'payments') },
        { key: '/finance/periods', label: 'Fiscal Periods', icon: iconFromFeature('finance', 'periods') },
        { key: '/finance/currencies', label: 'Currencies', icon: iconFromFeature('finance') },
        { key: '/finance/bank-recon', label: 'Bank Reconciliation', icon: iconFromFeature('finance', 'bank') },
        {
          key: '/finance/reports',
          label: 'Reports',
          children: [
            { key: '/finance/reports/trial-balance', label: 'Trial Balance' },
            { key: '/finance/reports/general-ledger', label: 'General Ledger' },
            { key: '/finance/reports/ar-aging', label: 'AR Aging' },
            { key: '/finance/reports/ap-aging', label: 'AP Aging' },
            { key: '/finance/reports/vat-return', label: 'VAT Return' },
          ],
        },
      ],
    },
    {
      key: 'inventory',
      icon: iconFromFeature('inventory') || <AppstoreOutlined />,
      label: 'Inventory',
      children: [
        { key: '/inventory', label: 'Inventory Control Tower', icon: iconFromFeature('inventory') },
        { key: '/inventory/products', label: 'Products', icon: iconFromFeature('inventory', 'products') },
        { key: '/inventory/warehouses', label: 'Warehouses', icon: iconFromFeature('inventory', 'warehouses') },
        { key: '/inventory/movements', label: 'Stock Movements', icon: iconFromFeature('inventory', 'stock_movements') },
        { key: '/inventory/requisitions', label: 'Requisitions', icon: iconFromFeature('inventory', 'requisitions_internal') },
        {
          key: '/inventory/valuation',
          label: 'Valuation',
          icon: <DollarOutlined />,
          children: [
        { key: '/inventory/valuation/settings', label: 'Valuation Settings' },
        { key: '/inventory/valuation/cost-layers', label: 'Cost Layers' },
        { key: '/inventory/valuation/report', label: 'Valuation Report' },
        { key: '/inventory/valuation/landed-cost', label: 'Landed Cost Adjustment' },
      ],
        },
      ],
    },
    {
      key: 'sales',
      icon: iconFromFeature('sales') || <ShoppingOutlined />,
      label: 'Sales & CRM',
      children: [
        { key: '/sales', label: 'Sales Control Tower', icon: iconFromFeature('sales') },
        { key: '/sales/customers', label: 'Customers', icon: iconFromFeature('sales', 'customers') },
        { key: '/sales/orders', label: 'Sales Orders', icon: iconFromFeature('sales', 'sales_orders') },
        { key: '/sales/pipeline', label: 'Sales Pipeline', icon: iconFromFeature('sales', 'pipeline') },
      ],
    },
    {
      key: 'policies',
      icon: iconFromFeature('policies', 'module') || <SafetyCertificateOutlined />,
      label: 'Policies',
      children: [
        { key: '/policies', label: 'Policies & SOPs' },
        { key: '/policies/my', label: 'My Acknowledgements' },
      ],
    },
    {
      key: 'ngo',
      icon: iconFromFeature('ngo', 'module') || <HeartOutlined />,
      label: 'NGO Governance',
      children: [
        { key: '/ngo/dashboard', label: 'Dashboard' },
        { key: '/ngo/programs', label: 'Programs' },
        { key: '/ngo/donors', label: 'Donors' },
        { key: '/ngo/compliance', label: 'Compliance' },
        { key: '/ngo/grant-governance', label: 'Grant Governance', icon: iconFromFeature('ngo', 'grant_governance') || <AuditOutlined /> },
      ],
    },
    {
      key: 'microfinance',
      icon: iconFromFeature('microfinance', 'module') || <BankOutlined />,
      label: 'Microfinance',
      children: [
        { key: '/microfinance/dashboard', label: 'Dashboard' },
        { key: '/microfinance/loans', label: 'Loans', icon: iconFromFeature('microfinance', 'loans') || <MoneyCollectOutlined /> },
        { key: '/microfinance/borrowers', label: 'Borrowers' },
        { key: '/microfinance/products', label: 'Loan Products' },
      ],
    },
    {
      key: 'procurement',
      icon: iconFromFeature('procurement') || <ShopOutlined />,
      label: 'Procurement',
      children: [
        { key: '/procurement', label: 'Procurement Control Tower', icon: iconFromFeature('procurement') },
        { key: '/procurement/suppliers', label: 'Suppliers', icon: iconFromFeature('procurement', 'vendors') },
        { key: '/procurement/orders', label: 'Purchase Orders', icon: iconFromFeature('procurement', 'purchase_orders') },
      ],
    },
    {
      key: 'nocode',
      icon: iconFromFeature('form_builder') || <FormOutlined />,
      label: 'No-Code Tools',
      children: [
        { key: '/forms', label: 'Form Builder', icon: iconFromFeature('form_builder') },
        { key: '/reports', label: 'Report Builder', icon: iconFromFeature('report_builder') },
        { key: '/workflows', label: 'Workflow Designer', icon: iconFromFeature('workflows') },
        { key: '/workflows/list', label: 'Workflow List' },
        { key: '/migration', label: 'Data Migration', icon: iconFromFeature('data_migration') },
      ],
    },
    {
      key: 'assets',
      icon: iconFromFeature('assets') || <ToolOutlined />,
      label: 'Asset Management',
      children: [
        { key: '/assets', label: 'Asset Command Center', icon: iconFromFeature('assets') },
        { key: '/assets/list', label: 'Asset Register', icon: iconFromFeature('assets', 'list') },
        { key: '/assets/maintenance', label: 'Maintenance Planner', icon: iconFromFeature('assets', 'maintenance') },
      ],
    },
    {
      key: 'budgets',
      icon: iconFromFeature('budgeting') || <PieChartOutlined />,
      label: 'Cost Centers & Budgeting',
      children: [
        { key: '/budgets', label: 'Budgeting Hub', icon: iconFromFeature('budgeting') },
        { key: '/budgets/entry', label: 'Budget Entry', icon: iconFromFeature('budgeting', 'list') },
        { key: '/budgets/approvals', label: 'Approval Queue', icon: iconFromFeature('budgeting', 'list') },
        { key: '/budgets/cost-centers', label: 'Cost Centers', icon: iconFromFeature('budgeting', 'cost_centers') },
        { key: '/budgets/item-codes', label: 'Item Codes', icon: iconFromFeature('budgeting', 'item_codes') },
        { key: '/budgets/uoms', label: 'Units of Measure', icon: iconFromFeature('budgeting', 'uoms') },
        { key: '/budgets/list', label: 'Budget Registry', icon: iconFromFeature('budgeting', 'list') },
        { key: '/budgets/monitor', label: 'Budget Monitor', icon: iconFromFeature('budgeting', 'monitor') },
        { key: '/budgets/gamification', label: 'Gamification', icon: iconFromFeature('budgeting', 'monitor') },
        { key: '/budgets/moderator', label: 'Moderator Dashboard', icon: iconFromFeature('budgeting', 'monitor') },
        { key: '/budgets/remark-templates', label: 'Remark Templates', icon: iconFromFeature('budgeting', 'list') },
      ],
    },
    {
      key: 'production',
      icon: iconFromFeature('production') || <ApartmentOutlined />,
      label: 'Production',
      children: [
        { key: '/production', label: 'Production Control Tower', icon: iconFromFeature('production') },
        { key: '/production/boms', label: 'Bills of Materials', icon: iconFromFeature('production', 'bom') },
        { key: '/production/work-orders', label: 'Work Orders', icon: iconFromFeature('production', 'work_orders') },
      ],
    },
    {
      key: 'hr',
      icon: iconFromFeature('hr') || <SolutionOutlined />,
      label: 'HR & Payroll',
      children: [
        { key: '/hr', label: 'People Operations Hub', icon: iconFromFeature('hr') },
        { key: '/hr/leave', label: 'Leave Management', icon: iconFromFeature('hr', 'leave') },
        { key: '/hr/advances-loans', label: 'Advances & Loans', icon: iconFromFeature('hr', 'advances_loans') },
        { key: '/hr/recruitment', label: 'Recruitment', icon: iconFromFeature('hr', 'recruitment') },
        { key: '/hr/onboarding', label: 'Onboarding', icon: iconFromFeature('hr', 'onboarding') },
        { key: '/hr/performance', label: 'Performance', icon: iconFromFeature('hr', 'performance') },
        { key: '/hr/exit-management', label: 'Exit Management', icon: iconFromFeature('hr', 'exit_management') },
        { key: '/hr/policies', label: 'Policy Management', icon: iconFromFeature('hr', 'policies') },
        { key: '/hr/attendance', label: 'Attendance', icon: iconFromFeature('hr', 'attendance') },
      ],
    },
    {
      key: 'projects',
      icon: iconFromFeature('projects') || <ProjectOutlined />,
      label: 'Projects',
      children: [
        { key: '/projects', label: 'Projects Command Center', icon: iconFromFeature('projects') },
        { key: '/projects/list', label: 'Projects List', icon: iconFromFeature('projects', 'list') },
        { key: '/projects/gantt', label: 'Gantt Planner', icon: iconFromFeature('projects', 'gantt') },
      ],
    },
  ];

  if (user?.is_system_admin || user?.is_staff) {
    menuItems.push({
      key: 'ai',
      icon: iconFromFeature('ai_companion') || <RobotOutlined />,
      label: 'AI Ops',
      children: [{ key: '/ai/training-review', label: 'Training Review' }],
    });
  }

  // Helper function to map menu keys to feature modules
  const getMenuFeatureModule = (menuKey) => {
    const moduleMap = {
      'finance': 'finance',
      'inventory': 'inventory',
      'sales': 'sales',
      'procurement': 'procurement',
      'production': 'production',
      'hr': 'hr',
      'projects': 'projects',
      'assets': 'assets',
      'budgets': 'budgeting',
      'ngo': 'ngo',
      'microfinance': 'microfinance',
      'workboard': 'tasks',
      'ai': 'ai_companion',
    };
    return moduleMap[menuKey];
  };

  // Helper function to add status badge to menu label
  const addStatusBadge = (label, status) => {
    if (!status || status === 'enabled') return label;

    const badgeColors = {
      'beta': 'blue',
      'coming_soon': 'orange',
      'deprecated': 'red',
    };

    const badgeLabels = {
      'beta': 'Beta',
      'coming_soon': 'Coming Soon',
      'deprecated': 'Deprecated',
    };

    return (
      <Space>
        {label}
        <Tag color={badgeColors[status]} style={{ fontSize: '10px', padding: '0 4px', marginRight: 0 }}>
          {badgeLabels[status]}
        </Tag>
      </Space>
    );
  };

  // Filter menu items based on feature toggles
  const filteredMenuItems = useMemo(() => {
    return menuItems
      .map((item) => {
        // Check if this menu item has a feature module
        const moduleKey = getMenuFeatureModule(item.key);

        if (moduleKey) {
          // Check if the module is enabled
          const isEnabled = isFeatureEnabled(moduleKey, 'module');
          if (!isEnabled) {
            return null; // Hide disabled modules
          }

          // Get feature details for status badges
          const feature = getFeature(moduleKey, 'module');
          if (feature?.status && feature.status !== 'enabled') {
            return {
              ...item,
              label: addStatusBadge(item.label, feature.status),
            };
          }
        }

        // Handle Inventory child-specific feature visibility
        if (item.key === 'inventory' && Array.isArray(item.children)) {
          const filteredChildren = item.children.filter((child) => {
            // Always show the Requisitions hub; tabs inside will honor feature flags
            if (child.key === '/inventory/requisitions') return true;
            return true;
          });
          return { ...item, children: filteredChildren };
        }

        if (item.key === 'procurement' && Array.isArray(item.children)) {
          const filteredChildren = item.children.filter((child) => {
            if (child.key === '/procurement/requisitions') return isFeatureEnabled('inventory', 'purchase_requisitions');
            return true;
          });
          return { ...item, children: filteredChildren };
        }

        // Handle no-code tools submenu - check each child feature
        if (item.key === 'nocode' && item.children) {
          const filteredChildren = item.children.filter((child) => {
            if (child.key === '/forms') return isFeatureEnabled('form_builder', 'module');
            if (child.key === '/reports') return isFeatureEnabled('report_builder', 'module');
            if (child.key === '/workflows') return isFeatureEnabled('workflows', 'module');
            if (child.key === '/migration') return isFeatureEnabled('data_migration', 'module');
            return true;
          });

          // Hide entire menu if no children are enabled
          if (filteredChildren.length === 0) return null;

          return {
            ...item,
            children: filteredChildren,
          };
        }

        return item;
      })
      .filter(Boolean); // Remove null items
  }, [menuItems, isFeatureEnabled, getFeature]);

  console.log('filteredMenuItems', filteredMenuItems);

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
        key: 'calendar_sync',
        icon: <LinkOutlined />,
        label: 'Calendar Sync',
        onClick: () => navigate('/settings/calendar-sync'),
      },
      {
        key: 'refresh_features',
        icon: <BranchesOutlined />,
        label: 'Refresh Features',
        onClick: refreshFeatures,
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

  const severityColor = (sev) => {
    switch ((sev || '').toLowerCase()) {
      case 'warning':
        return 'orange';
      case 'critical':
        return 'red';
      case 'info':
      default:
        return 'blue';
    }
  };

  const notifItems = (notifications || []).slice(0, 10).map((n) => ({
    key: String(n.id),
    label: (
      <div style={{ maxWidth: 360 }}>
        <Space direction="vertical" size={2} style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <Typography.Text strong ellipsis style={{ maxWidth: 260 }}>{n.title}</Typography.Text>
            <Typography.Text type="secondary" style={{ whiteSpace: 'nowrap' }}>
              {n.created_at ? dayjs(n.created_at).format('MMM D, HH:mm') : ''}
            </Typography.Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {n.severity ? <Tag color={severityColor(n.severity)}>{String(n.severity).toUpperCase()}</Tag> : null}
            {n.body ? (
              <Typography.Text type="secondary" ellipsis style={{ flex: 1 }}>
                {n.body}
              </Typography.Text>
            ) : null}
          </div>
        </Space>
      </div>
    ),
  }));
  const notifMenu = {
    items: [
      ...notifItems,
      { type: 'divider' },
      { key: '__mark_all', label: 'Mark all read' },
      { key: '__view_all', label: 'See all notifications' },
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
          items={filteredMenuItems}
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
          TWIST ERP Â©2025 Transform, Integrate, Simplify, Track
        </Footer>
        <Modal
          title="Create Task"
          open={createVisible}
          onCancel={() => setCreateVisible(false)}
          onOk={async () => {
            try {
              const values = await form.validateFields();
              if (!currentCompany?.id) {
                message.error('Please select a company (top-left) before creating a task.');
                return;
              }
              // Ensure header context is present
              try {
                const stored = localStorage.getItem('twist-active-company');
                if (!stored || String(stored) !== String(currentCompany.id)) {
                  localStorage.setItem('twist-active-company', String(currentCompany.id));
                }
              } catch (_) {}

              setCreating(true);

              const payload = {
                task_type: 'personal',
                title: values.title,
                description: values.description || '',
                due_date: values.due_date ? values.due_date.toISOString() : null,
                assigned_to: user?.id,
                priority: values.priority || 'normal',
                visibility_scope: 'private',
                recurrence: values.recurrence || 'none',
                recurrence_until: values.recurrence_until ? values.recurrence_until.toISOString() : null,
              };

              const postTask = async () => api.post('/api/v1/tasks/', payload);

              try {
                await postTask();
              } catch (err) {
                // If company context still missing on server, set session and retry once
                const status = err?.response?.status;
                if (status === 400) {
                  try {
                    await api.post('/api/v1/companies/companies/activate/', { id: currentCompany.id });
                    await postTask();
                  } catch (e2) {
                    const detail = e2?.response?.data?.detail || 'Failed to create task';
                    message.error(detail);
                    return;
                  }
                } else {
                  const detail = err?.response?.data?.detail || 'Failed to create task';
                  message.error(detail);
                  return;
                }
              }
              setCreateVisible(false);
              form.resetFields();
            } catch (e) {
              // validation or unexpected
              if (e?.errorFields) {
                // AntD validation already shows messages
              } else {
                message.error('Unable to create task');
              }
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
        <AIWidget />
    </Layout>
    </Layout>
  );
};

export default MainLayout;
