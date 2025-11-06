import React from 'react';
import ConfigProvider from 'antd/es/config-provider';
import { App as AntApp } from 'antd';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { FeatureProvider } from './contexts/FeatureContext';
import { FeatureGuard } from './components/FeatureGuard';
import LoginPage from './pages/LoginPage';

// Layouts
import MainLayout from './layouts/MainLayout';

// Dashboard
import Dashboard from './pages/Dashboard/Dashboard';

// Finance
import FinanceWorkspace from './pages/Finance/FinanceWorkspace';
import Currencies from './pages/Finance/Currencies';
import CalendarSync from './pages/Settings/CalendarSync';
import AccountsList from './pages/Finance/Accounts/AccountsList';
import JournalVouchersList from './pages/Finance/Journals/JournalVouchers';
import InvoicesList from './pages/Finance/Invoices/InvoicesList';
import PaymentsList from './pages/Finance/Payments/PaymentsList';
import PeriodsList from './pages/Finance/Periods/PeriodsList';
import BankReconciliation from './pages/Finance/Bank/BankReconciliation';
import TrialBalance from './pages/Finance/Reports/TrialBalance';
import GeneralLedger from './pages/Finance/Reports/GeneralLedger';
import ARAging from './pages/Finance/Reports/ARAging';
import APAging from './pages/Finance/Reports/APAging';
import VATReturn from './pages/Finance/Reports/VATReturn';

// Inventory
import InventoryWorkspace from './pages/Inventory/InventoryWorkspace';
import ProductsList from './pages/Inventory/Products/ProductsList';
import WarehousesList from './pages/Inventory/Warehouses/WarehousesList';
import StockMovements from './pages/Inventory/StockMovements/StockMovements';
import InternalRequisitions from './pages/Inventory/Requisitions/InternalRequisitions';
import PurchaseRequisitions from './pages/Inventory/Requisitions/PurchaseRequisitions';
import RequisitionsHub from './pages/Inventory/Requisitions/RequisitionsHub';
import { ValuationSettings, CostLayersView, ValuationReport } from './pages/Inventory/Valuation';
import LandedCostAdjustment from './pages/Inventory/Valuation/LandedCostAdjustment';

// Sales & CRM
import SalesWorkspace from './pages/Sales/SalesWorkspace';
import CustomersList from './pages/Sales/Customers/CustomersList';
import PoliciesList from './pages/Policies/PoliciesList';
import MyAcknowledgements from './pages/Policies/MyAcknowledgements';
import ProgramsList from './pages/NGO/ProgramsList';
import DonorsList from './pages/NGO/DonorsList';
import Compliance from './pages/NGO/Compliance';
import NgoDashboard from './pages/NGO/NgoDashboard';
import GrantGovernance from './pages/NGO/GrantGovernance';
import LoansList from './pages/Microfinance/LoansList';
import BorrowersList from './pages/Microfinance/BorrowersList';
import MFProductsList from './pages/Microfinance/ProductsList';
import MicrofinanceDashboard from './pages/Microfinance/MicrofinanceDashboard';
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
import WorkflowList from './pages/Workflows/WorkflowList';
import DataMigration from './pages/DataMigration/DataMigration';
import ReportBuilder from './pages/ReportBuilder/ReportBuilder';
import MyApprovals from './pages/Approvals/MyApprovals';

// Assets
import AssetsWorkspace from './pages/Assets/AssetsWorkspace';
import AssetsList from './pages/Assets/AssetsList';
import AssetMaintenance from './pages/Assets/AssetMaintenance';

// Budgeting
import BudgetingWorkspace from './pages/Budgeting/BudgetingWorkspace';
import BudgetsList from './pages/Budgeting/BudgetsList';
import BudgetMonitor from './pages/Budgeting/BudgetMonitor';
import ItemCodes from './pages/Budgeting/ItemCodes';
import Uoms from './pages/Budgeting/Uoms';
import CostCenters from './pages/Budgeting/CostCenters';
import BudgetEntry from './pages/Budgeting/BudgetEntry';
import ApprovalQueue from './pages/Budgeting/ApprovalQueue';
import ModeratorDashboard from './pages/Budgeting/ModeratorDashboard';
import RemarkTemplates from './pages/Budgeting/RemarkTemplates';
import Gamification from './pages/Budgeting/Gamification';

// HR & Payroll
import HRWorkspace from './pages/HR/HRWorkspace';
import EmployeesList from './pages/HR/Employees/EmployeesList';
import Attendance from './pages/HR/Attendance/Attendance';
import PayrollList from './pages/HR/Payroll/PayrollList';
import LeaveManagement from './pages/HR/LeaveManagement';
import AdvancesLoansManagement from './pages/HR/AdvancesLoansManagement';
import RecruitmentManagement from './pages/HR/RecruitmentManagement';
import OnboardingManagement from './pages/HR/OnboardingManagement';
import PerformanceManagement from './pages/HR/PerformanceManagement';
import ExitManagement from './pages/HR/ExitManagement';
import PolicyManagement from './pages/HR/PolicyManagement';
import AttendanceManagement from './pages/HR/AttendanceManagement';

// Projects
import ProjectsWorkspace from './pages/Projects/ProjectsWorkspace';
import ProjectsList from './pages/Projects/ProjectsList';
import ProjectGantt from './pages/Projects/ProjectGantt';

import AiTrainingReview from './pages/AI/AiTrainingReview';
import OnboardingWizard from './pages/Onboarding/OnboardingWizard';
import Settings from './pages/Settings/Settings';
import MyTasks from './pages/Tasks/MyTasks';
import TeamTasks from './pages/Tasks/TeamTasks';
import NotificationCenter from './pages/Notifications/NotificationCenter';

// Company Management
import CompanyManagement from './pages/Company/CompanyManagement';

// Organization Hierarchy
import CompanyGroupManagement from './pages/Organization/CompanyGroupManagement';
import BranchManagement from './pages/Organization/BranchManagement';
import DepartmentManagement from './pages/Organization/DepartmentManagement';
import UserAccessManagement from './pages/Organization/UserAccessManagement';

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
    return <div>Loading...</div>;
  }

  return (
    <ConfigProvider theme={theme}>
      <AntApp>
        <FeatureProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" />} />
              <Route path="/*" element={isAuthenticated ? <MainApp /> : <Navigate to="/login" />} />
            </Routes>
          </BrowserRouter>
        </FeatureProvider>
      </AntApp>
    </ConfigProvider>
  );
}

const MainApp = () => {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />

        {/* Finance Module */}
        <Route path="/finance" element={<FeatureGuard module="finance"><FinanceWorkspace /></FeatureGuard>} />
        <Route path="/finance/accounts" element={<FeatureGuard module="finance" feature="chart_of_accounts"><AccountsList /></FeatureGuard>} />
        <Route path="/finance/journals" element={<FeatureGuard module="finance" feature="journal_vouchers"><JournalVouchersList /></FeatureGuard>} />
        <Route path="/finance/invoices" element={<FeatureGuard module="finance"><InvoicesList /></FeatureGuard>} />
        <Route path="/finance/payments" element={<FeatureGuard module="finance"><PaymentsList /></FeatureGuard>} />
        <Route path="/finance/periods" element={<FeatureGuard module="finance"><PeriodsList /></FeatureGuard>} />
        <Route path="/finance/currencies" element={<FeatureGuard module="finance"><Currencies /></FeatureGuard>} />
        <Route path="/finance/bank-recon" element={<FeatureGuard module="finance"><BankReconciliation /></FeatureGuard>} />
        <Route path="/finance/reports/trial-balance" element={<FeatureGuard module="finance"><TrialBalance /></FeatureGuard>} />
        <Route path="/finance/reports/general-ledger" element={<FeatureGuard module="finance"><GeneralLedger /></FeatureGuard>} />
        <Route path="/finance/reports/ar-aging" element={<FeatureGuard module="finance"><ARAging /></FeatureGuard>} />
        <Route path="/finance/reports/ap-aging" element={<FeatureGuard module="finance"><APAging /></FeatureGuard>} />
        <Route path="/finance/reports/vat-return" element={<FeatureGuard module="finance"><VATReturn /></FeatureGuard>} />
        <Route path="/settings/calendar-sync" element={<CalendarSync />} />

        {/* Inventory Module */}
        <Route path="/inventory" element={<FeatureGuard module="inventory"><InventoryWorkspace /></FeatureGuard>} />
        <Route path="/inventory/products" element={<FeatureGuard module="inventory" feature="products"><ProductsList /></FeatureGuard>} />
        <Route path="/inventory/warehouses" element={<FeatureGuard module="inventory"><WarehousesList /></FeatureGuard>} />
        <Route path="/inventory/movements" element={<FeatureGuard module="inventory"><StockMovements /></FeatureGuard>} />
        <Route path="/inventory/requisitions" element={<FeatureGuard module="inventory"><RequisitionsHub /></FeatureGuard>} />
        <Route path="/inventory/requisitions/internal" element={<FeatureGuard module="inventory" feature="requisitions_internal"><InternalRequisitions /></FeatureGuard>} />
        <Route path="/inventory/requisitions/purchase" element={<FeatureGuard module="inventory" feature="purchase_requisitions"><PurchaseRequisitions /></FeatureGuard>} />
        <Route path="/inventory/valuation/settings" element={<FeatureGuard module="inventory"><ValuationSettings /></FeatureGuard>} />
        <Route path="/inventory/valuation/cost-layers" element={<FeatureGuard module="inventory"><CostLayersView /></FeatureGuard>} />
      <Route path="/inventory/valuation/report" element={<FeatureGuard module="inventory"><ValuationReport /></FeatureGuard>} />
      <Route path="/inventory/valuation/landed-cost" element={<FeatureGuard module="inventory"><LandedCostAdjustment /></FeatureGuard>} />

        {/* Sales Module */}
        <Route path="/sales" element={<FeatureGuard module="sales"><SalesWorkspace /></FeatureGuard>} />
        <Route path="/sales/customers" element={<FeatureGuard module="sales" feature="customers"><CustomersList /></FeatureGuard>} />
        <Route path="/sales/pipeline" element={<FeatureGuard module="sales"><SalesPipeline /></FeatureGuard>} />
        <Route path="/sales/orders" element={<FeatureGuard module="sales" feature="sales_orders"><SalesOrdersList /></FeatureGuard>} />
      <Route path="/policies" element={<PoliciesList />} />
      <Route path="/policies/my" element={<MyAcknowledgements />} />
      <Route path="/ngo/programs" element={<ProgramsList />} />
      <Route path="/ngo/donors" element={<DonorsList />} />
      <Route path="/ngo/compliance" element={<Compliance />} />
        <Route path="/ngo/grant-governance" element={<FeatureGuard module="ngo" feature="grant_governance"><GrantGovernance /></FeatureGuard>} />
      <Route path="/ngo/dashboard" element={<NgoDashboard />} />
      <Route path="/microfinance/loans" element={<LoansList />} />
      <Route path="/microfinance/borrowers" element={<BorrowersList />} />
      <Route path="/microfinance/products" element={<MFProductsList />} />
      <Route path="/microfinance/dashboard" element={<MicrofinanceDashboard />} />
      {/* Procurement Module */}
      <Route path="/procurement" element={<FeatureGuard module="procurement"><ProcurementWorkspace /></FeatureGuard>} />
      <Route path="/procurement/suppliers" element={<FeatureGuard module="procurement" feature="vendors"><SuppliersList /></FeatureGuard>} />
      <Route path="/procurement/orders" element={<FeatureGuard module="procurement" feature="purchase_orders"><PurchaseOrdersList /></FeatureGuard>} />
      

      {/* Production Module */}
      <Route path="/production" element={<FeatureGuard module="production"><ProductionWorkspace /></FeatureGuard>} />
      <Route path="/production/boms" element={<FeatureGuard module="production" feature="bom"><ProductionBOMList /></FeatureGuard>} />
      <Route path="/production/work-orders" element={<FeatureGuard module="production" feature="work_orders"><ProductionWorkOrders /></FeatureGuard>} />

      {/* Assets Module */}
      <Route path="/assets" element={<FeatureGuard module="assets"><AssetsWorkspace /></FeatureGuard>} />
      <Route path="/assets/list" element={<FeatureGuard module="assets"><AssetsList /></FeatureGuard>} />
      <Route path="/assets/maintenance" element={<FeatureGuard module="assets"><AssetMaintenance /></FeatureGuard>} />

      {/* Budgeting Module */}
      <Route path="/budgets" element={<FeatureGuard module="budgeting"><BudgetingWorkspace /></FeatureGuard>} />
      <Route path="/budgets/entry" element={<FeatureGuard module="budgeting"><BudgetEntry /></FeatureGuard>} />
      <Route path="/budgets/approvals" element={<FeatureGuard module="budgeting"><ApprovalQueue /></FeatureGuard>} />
      <Route path="/budgets/list" element={<FeatureGuard module="budgeting"><BudgetsList /></FeatureGuard>} />
       <Route path="/budgets/monitor" element={<FeatureGuard module="budgeting"><BudgetMonitor /></FeatureGuard>} />
       <Route path="/budgets/moderator" element={<FeatureGuard module="budgeting"><ModeratorDashboard /></FeatureGuard>} />
       <Route path="/budgets/gamification" element={<FeatureGuard module="budgeting"><Gamification /></FeatureGuard>} />
       <Route path="/budgets/moderator" element={<FeatureGuard module="budgeting"><ModeratorDashboard /></FeatureGuard>} />
       <Route path="/budgets/remark-templates" element={<FeatureGuard module="budgeting"><RemarkTemplates /></FeatureGuard>} />
       <Route path="/budgets/item-codes" element={<FeatureGuard module="budgeting"><ItemCodes /></FeatureGuard>} />
      <Route path="/budgets/uoms" element={<FeatureGuard module="budgeting"><Uoms /></FeatureGuard>} />
      <Route path="/budgets/cost-centers" element={<FeatureGuard module="budgeting"><CostCenters /></FeatureGuard>} />

      {/* HR Module */}
      <Route path="/hr" element={<FeatureGuard module="hr"><HRWorkspace /></FeatureGuard>} />
      <Route path="/hr/employees" element={<FeatureGuard module="hr" feature="employees"><EmployeesList /></FeatureGuard>} />
      <Route path="/hr/attendance" element={<FeatureGuard module="hr"><Attendance /></FeatureGuard>} />
      <Route path="/hr/payroll" element={<FeatureGuard module="hr" feature="payroll"><PayrollList /></FeatureGuard>} />
      <Route path="/hr/leave" element={<FeatureGuard module="hr"><LeaveManagement /></FeatureGuard>} />
      <Route path="/hr/advances-loans" element={<FeatureGuard module="hr"><AdvancesLoansManagement /></FeatureGuard>} />
      <Route path="/hr/recruitment" element={<FeatureGuard module="hr"><RecruitmentManagement /></FeatureGuard>} />
      <Route path="/hr/onboarding" element={<FeatureGuard module="hr"><OnboardingManagement /></FeatureGuard>} />
      <Route path="/hr/performance" element={<FeatureGuard module="hr"><PerformanceManagement /></FeatureGuard>} />
      <Route path="/hr/exit-management" element={<FeatureGuard module="hr"><ExitManagement /></FeatureGuard>} />
      <Route path="/hr/policies" element={<FeatureGuard module="hr"><PolicyManagement /></FeatureGuard>} />
      <Route path="/hr/attendance/management" element={<FeatureGuard module="hr"><AttendanceManagement /></FeatureGuard>} />

      {/* Projects Module */}
      <Route path="/projects" element={<FeatureGuard module="projects"><ProjectsWorkspace /></FeatureGuard>} />
      <Route path="/projects/list" element={<FeatureGuard module="projects"><ProjectsList /></FeatureGuard>} />
      <Route path="/projects/gantt" element={<FeatureGuard module="projects"><ProjectGantt /></FeatureGuard>} />

      {/* AI & No-Code Tools */}
      <Route path="/ai/training-review" element={<FeatureGuard module="ai_companion"><AiTrainingReview /></FeatureGuard>} />
      <Route path="/forms" element={<FeatureGuard module="form_builder"><FormBuilder /></FeatureGuard>} />
      <Route path="/reports" element={<FeatureGuard module="report_builder"><ReportBuilder /></FeatureGuard>} />
      <Route path="/schemas" element={<FeatureGuard module="form_builder"><SchemaDesigner /></FeatureGuard>} />
      <Route path="/forms/entities/:slug" element={<FeatureGuard module="form_builder"><EntityWorkspace /></FeatureGuard>} />
      <Route path="/workflows" element={<FeatureGuard module="workflows"><WorkflowDesigner /></FeatureGuard>} />
      <Route path="/workflows/list" element={<FeatureGuard module="workflows"><WorkflowList /></FeatureGuard>} />
      <Route path="/migration" element={<FeatureGuard module="data_migration"><DataMigration /></FeatureGuard>} />
      <Route path="/approvals" element={<FeatureGuard module="workflows"><MyApprovals /></FeatureGuard>} />
      <Route path="/onboarding" element={<OnboardingWizard />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/settings/profile" element={<Settings />} />
      <Route path="/settings/preferences" element={<Settings />} />
      {/* Tasks & Notifications */}
      <Route path="/tasks" element={<FeatureGuard module="tasks"><MyTasks /></FeatureGuard>} />
      <Route path="/tasks/my" element={<FeatureGuard module="tasks"><MyTasks /></FeatureGuard>} />
      <Route path="/tasks/team" element={<FeatureGuard module="tasks"><TeamTasks /></FeatureGuard>} />
      <Route path="/notifications" element={<FeatureGuard module="notifications"><NotificationCenter /></FeatureGuard>} />

      {/* Company & Organization Management */}
      <Route path="/company-management" element={<CompanyManagement />} />
      <Route path="/organization/groups" element={<CompanyGroupManagement />} />
      <Route path="/organization/branches" element={<BranchManagement />} />
      <Route path="/organization/departments" element={<DepartmentManagement />} />
      <Route path="/organization/user-access" element={<UserAccessManagement />} />
    </Routes>
  </MainLayout>
);

};

export default App;

