import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';

// Layouts
import MainLayout from './layouts/MainLayout';

// Dashboard
import Dashboard from './pages/Dashboard/Dashboard';

// Finance
import FinanceWorkspace from './pages/Finance/FinanceWorkspace';
import AccountsList from './pages/Finance/Accounts/AccountsList';
import JournalVouchersList from './pages/Finance/Journals/JournalVouchers';
import InvoicesList from './pages/Finance/Invoices/InvoicesList';
import PaymentsList from './pages/Finance/Payments/PaymentsList';

// Inventory
import InventoryWorkspace from './pages/Inventory/InventoryWorkspace';
import ProductsList from './pages/Inventory/Products/ProductsList';
import WarehousesList from './pages/Inventory/Warehouses/WarehousesList';
import StockMovements from './pages/Inventory/StockMovements/StockMovements';

// Sales & CRM
import SalesWorkspace from './pages/Sales/SalesWorkspace';
import CustomersList from './pages/Sales/Customers/CustomersList';
import SalesPipeline from './pages/Sales/Pipeline/SalesPipeline';
import SalesOrdersList from './pages/Sales/Orders/SalesOrdersList';

// Procurement
import ProcurementWorkspace from './pages/Procurement/ProcurementWorkspace';
import SuppliersList from './pages/Procurement/Suppliers/SuppliersList';
import PurchaseOrdersList from './pages/Procurement/Orders/PurchaseOrdersList';

// Production
import ProductionWorkspace from './pages/Production/ProductionWorkspace';
import ProductionBOMList from './pages/Production/BOMList';
import ProductionWorkOrders from './pages/Production/WorkOrders';

// No-Code tools
import FormBuilder from './pages/FormBuilder/FormBuilder';
import SchemaDesigner from './pages/FormBuilder/SchemaDesigner';
import EntityWorkspace from './pages/FormBuilder/EntityWorkspace';
import WorkflowDesigner from './pages/Workflows/WorkflowDesigner';
import DataMigration from './pages/DataMigration/DataMigration';
// Assets
import AssetsWorkspace from './pages/Assets/AssetsWorkspace';
import AssetsList from './pages/Assets/AssetsList';
import AssetMaintenance from './pages/Assets/AssetMaintenance';
// Budgeting
import BudgetingWorkspace from './pages/Budgeting/BudgetingWorkspace';
import BudgetsList from './pages/Budgeting/BudgetsList';
import BudgetMonitor from './pages/Budgeting/BudgetMonitor';
// HR & Payroll
import HRWorkspace from './pages/HR/HRWorkspace';
import EmployeesList from './pages/HR/Employees/EmployeesList';
import Attendance from './pages/HR/Attendance/Attendance';
import PayrollList from './pages/HR/Payroll/PayrollList';
// Projects
import ProjectsWorkspace from './pages/Projects/ProjectsWorkspace';
import ProjectsList from './pages/Projects/ProjectsList';
import ProjectGantt from './pages/Projects/ProjectGantt';
import AiTrainingReview from './pages/AI/AiTrainingReview';
import OnboardingWizard from './pages/Onboarding/OnboardingWizard';
import Settings from './pages/Settings/Settings';

// Theme configuration
const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

function App() {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>; // Or a proper spinner component
    }

    return (
        <ConfigProvider theme={theme}>
            <Router>
                <Routes>
                    <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" />} />
                    <Route path="/*" element={isAuthenticated ? <MainApp /> : <Navigate to="/login" />} />
                </Routes>
            </Router>
        </ConfigProvider>
    );
}

// A new component to hold the main application layout and routes
const MainApp = () => {
    return (
        <MainLayout>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/finance" element={<FinanceWorkspace />} />
                <Route path="/finance/accounts" element={<AccountsList />} />
                <Route path="/finance/journals" element={<JournalVouchersList />} />
                <Route path="/finance/invoices" element={<InvoicesList />} />
                <Route path="/finance/payments" element={<PaymentsList />} />
                <Route path="/inventory" element={<InventoryWorkspace />} />
                <Route path="/inventory/products" element={<ProductsList />} />
                <Route path="/inventory/warehouses" element={<WarehousesList />} />
                <Route path="/inventory/movements" element={<StockMovements />} />
                <Route path="/sales" element={<SalesWorkspace />} />
                <Route path="/sales/customers" element={<CustomersList />} />
                <Route path="/sales/pipeline" element={<SalesPipeline />} />
                <Route path="/sales/orders" element={<SalesOrdersList />} />
                <Route path="/procurement" element={<ProcurementWorkspace />} />
                <Route path="/procurement/suppliers" element={<SuppliersList />} />
                <Route path="/procurement/orders" element={<PurchaseOrdersList />} />
                <Route path="/production" element={<ProductionWorkspace />} />
                <Route path="/production/boms" element={<ProductionBOMList />} />
                <Route path="/production/work-orders" element={<ProductionWorkOrders />} />
                <Route path="/assets" element={<AssetsWorkspace />} />
                <Route path="/assets/list" element={<AssetsList />} />
                <Route path="/assets/maintenance" element={<AssetMaintenance />} />
                <Route path="/budgets" element={<BudgetingWorkspace />} />
                <Route path="/budgets/list" element={<BudgetsList />} />
                <Route path="/budgets/monitor" element={<BudgetMonitor />} />
                <Route path="/hr" element={<HRWorkspace />} />
                <Route path="/hr/employees" element={<EmployeesList />} />
                <Route path="/hr/attendance" element={<Attendance />} />
                <Route path="/hr/payroll" element={<PayrollList />} />
                <Route path="/projects" element={<ProjectsWorkspace />} />
                <Route path="/projects/list" element={<ProjectsList />} />
                <Route path="/projects/gantt" element={<ProjectGantt />} />
                <Route path="/ai/training-review" element={<AiTrainingReview />} />
                <Route path="/forms" element={<FormBuilder />} />
                <Route path="/schemas" element={<SchemaDesigner />} />
                <Route path="/forms/entities/:slug" element={<EntityWorkspace />} />
                <Route path="/workflows" element={<WorkflowDesigner />} />
                <Route path="/migration" element={<DataMigration />} />
                <Route path="/onboarding" element={<OnboardingWizard />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/settings/profile" element={<Settings />} />
                <Route path="/settings/preferences" element={<Settings />} />
                {/* Add other routes for your pages here */}
            </Routes>
        </MainLayout>
    );
};

export default App;
