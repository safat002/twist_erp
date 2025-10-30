import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, message } from 'antd';
import { useAuth } from './contexts/AuthContext';
import { useCompany } from './contexts/CompanyContext';

// Layouts
import MainLayout from './layouts/MainLayout';
import AuthLayout from './layouts/AuthLayout';

// Auth Pages
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';

// Dashboard
import Dashboard from './pages/Dashboard/Dashboard';

// Finance
import AccountsList from './pages/Finance/Accounts/AccountsList';
import JournalVouchers from './pages/Finance/Journals/JournalVouchers';
import InvoicesList from './pages/Finance/Invoices/InvoicesList';
import PaymentsList from './pages/Finance/Payments/PaymentsList';

// Inventory
import ProductsList from './pages/Inventory/Products/ProductsList';
import WarehousesList from './pages/Inventory/Warehouses/WarehousesList';
import StockMovements from './pages/Inventory/StockMovements/StockMovements';

// Sales
import CustomersList from './pages/Sales/Customers/CustomersList';
import SalesOrdersList from './pages/Sales/Orders/SalesOrdersList';
import SalesPipeline from './pages/Sales/Pipeline/SalesPipeline';

// Procurement
import SuppliersList from './pages/Procurement/Suppliers/SuppliersList';
import PurchaseOrdersList from './pages/Procurement/Orders/PurchaseOrdersList';

// Data Migration
import DataMigration from './pages/DataMigration/DataMigration';

// Form Builder
import FormBuilder from './pages/FormBuilder/FormBuilder';
import FormList from './pages/FormBuilder/FormList';

// Workflows
import WorkflowDesigner from './pages/Workflows/WorkflowDesigner';
import WorkflowList from './pages/Workflows/WorkflowList';

// Assets
import AssetsList from './pages/Assets/AssetsList';
import AssetMaintenance from './pages/Assets/AssetMaintenance';

// Budgeting
import BudgetsList from './pages/Budgeting/BudgetsList';
import BudgetMonitor from './pages/Budgeting/BudgetMonitor';

// HR
import EmployeesList from './pages/HR/Employees/EmployeesList';
import Attendance from './pages/HR/Attendance/Attendance';
import PayrollList from './pages/HR/Payroll/PayrollList';

// Projects
import ProjectsList from './pages/Projects/ProjectsList';
import ProjectGantt from './pages/Projects/ProjectGantt';

// AI Companion
import AIWidget from './components/AIAssistant/AIWidget';

// Settings
import Settings from './pages/Settings/Settings';

// Theme configuration
const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

function App() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { currentCompany } = useCompany();

  if (authLoading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <ConfigProvider theme={theme}>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/auth" element={<AuthLayout />}>
            <Route path="login" element={<Login />} />
            <Route path="register" element={<Register />} />
          </Route>

          {/* Protected Routes */}
          <Route
            path="/*"
            element={
              isAuthenticated ? (
                <MainLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />

                    {/* Finance */}
                    <Route path="/finance/accounts" element={<AccountsList />} />
                    <Route path="/finance/journals" element={<JournalVouchers />} />
                    <Route path="/finance/invoices" element={<InvoicesList />} />
                    <Route path="/finance/payments" element={<PaymentsList />} />

                    {/* Inventory */}
                    <Route path="/inventory/products" element={<ProductsList />} />
                    <Route path="/inventory/warehouses" element={<WarehousesList />} />
                    <Route path="/inventory/movements" element={<StockMovements />} />

                    {/* Sales */}
                    <Route path="/sales/customers" element={<CustomersList />} />
                    <Route path="/sales/orders" element={<SalesOrdersList />} />
                    <Route path="/sales/pipeline" element={<SalesPipeline />} />

                    {/* Procurement */}
                    <Route path="/procurement/suppliers" element={<SuppliersList />} />
                    <Route path="/procurement/orders" element={<PurchaseOrdersList />} />

                    {/* Data Migration */}
                    <Route path="/migration" element={<DataMigration />} />

                    {/* Form Builder */}
                    <Route path="/forms" element={<FormList />} />
                    <Route path="/forms/builder/:id?" element={<FormBuilder />} />

                    {/* Workflows */}
                    <Route path="/workflows" element={<WorkflowList />} />
                    <Route path="/workflows/designer/:id?" element={<WorkflowDesigner />} />

                    {/* Assets */}
                    <Route path="/assets" element={<AssetsList />} />
                    <Route path="/assets/maintenance" element={<AssetMaintenance />} />

                    {/* Budgeting */}
                    <Route path="/budgets" element={<BudgetsList />} />
                    <Route path="/budgets/monitor" element={<BudgetMonitor />} />

                    {/* HR */}
                    <Route path="/hr/employees" element={<EmployeesList />} />
                    <Route path="/hr/attendance" element={<Attendance />} />
                    <Route path="/hr/payroll" element={<PayrollList />} />

                    {/* Projects */}
                    <Route path="/projects" element={<ProjectsList />} />
                    <Route path="/projects/:id/gantt" element={<ProjectGantt />} />

                    {/* Settings */}
                    <Route path="/settings" element={<Settings />} />
                  </Routes>

                  {/* AI Assistant Widget - Always visible */}
                  <AIWidget />
                </MainLayout>
              ) : (
                <Navigate to="/auth/login" replace />
              )
            }
          />
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
