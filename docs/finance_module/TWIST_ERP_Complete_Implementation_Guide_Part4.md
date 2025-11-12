# TWIST ERP FINANCE MODULE - IMPLEMENTATION GUIDE PART 4
## Frontend Implementation - React UI & User Experience

---

## 5. FRONTEND ARCHITECTURE

### 5.1 State Management Setup

**File: `frontend/src/store/index.ts`**

```typescript
import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { financeApi } from '../api/financeApi';
import authReducer from './slices/authSlice';
import companyReducer from './slices/companySlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    [financeApi.reducerPath]: financeApi.reducer,
    auth: authReducer,
    company: companyReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(financeApi.middleware),
});

setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### 5.2 API Client with RTK Query

**File: `frontend/src/api/financeApi.ts`**

```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { 
  JournalVoucher, 
  FinancialStatements, 
  FiscalPeriod,
  GLAccount 
} from '../types/finance';

export const financeApi = createApi({
  reducerPath: 'financeApi',
  baseQuery: fetchBaseQuery({
    baseUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as any).auth.token;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      const company = (getState() as any).company.currentCompany;
      if (company) {
        headers.set('X-Company-ID', company.id);
      }
      return headers;
    },
  }),
  tagTypes: ['JournalVoucher', 'GLAccount', 'Period', 'Report'],
  endpoints: (builder) => ({
    // Journal Vouchers
    getJournalVouchers: builder.query<JournalVoucher[], { status?: string; period?: string }>({
      query: (params) => ({
        url: '/finance/journal-vouchers/',
        params,
      }),
      providesTags: ['JournalVoucher'],
    }),
    
    getJournalVoucher: builder.query<JournalVoucher, string>({
      query: (id) => `/finance/journal-vouchers/${id}/`,
      providesTags: (result, error, id) => [{ type: 'JournalVoucher', id }],
    }),
    
    createJournalVoucher: builder.mutation<JournalVoucher, Partial<JournalVoucher>>({
      query: (body) => ({
        url: '/finance/journal-vouchers/',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['JournalVoucher'],
    }),
    
    submitJournalVoucher: builder.mutation<void, string>({
      query: (id) => ({
        url: `/finance/journal-vouchers/${id}/submit/`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, id) => [{ type: 'JournalVoucher', id }],
    }),
    
    approveJournalVoucher: builder.mutation<void, string>({
      query: (id) => ({
        url: `/finance/journal-vouchers/${id}/approve/`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, id) => [{ type: 'JournalVoucher', id }],
    }),
    
    postJournalVoucher: builder.mutation<void, string>({
      query: (id) => ({
        url: `/finance/journal-vouchers/${id}/post_to_gl/`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'JournalVoucher', id },
        'Report'
      ],
    }),
    
    // Financial Statements - ONE CLICK GENERATOR
    getFinancialStatements: builder.query<
      FinancialStatements, 
      { period: string; comparisonPeriod?: string; format?: 'json' | 'pdf' | 'excel' }
    >({
      query: (params) => ({
        url: '/finance/reports/financial-statements/',
        params,
        responseHandler: (response) => {
          // Handle different formats
          if (params.format === 'pdf' || params.format === 'excel') {
            return response.blob();
          }
          return response.json();
        },
      }),
      providesTags: ['Report'],
    }),
    
    // Chart of Accounts
    getGLAccounts: builder.query<GLAccount[], void>({
      query: () => '/finance/chart-of-accounts/',
      providesTags: ['GLAccount'],
    }),
    
    // Periods
    getFiscalPeriods: builder.query<FiscalPeriod[], { status?: string }>({
      query: (params) => ({
        url: '/finance/periods/',
        params,
      }),
      providesTags: ['Period'],
    }),
  }),
});

export const {
  useGetJournalVouchersQuery,
  useGetJournalVoucherQuery,
  useCreateJournalVoucherMutation,
  useSubmitJournalVoucherMutation,
  useApproveJournalVoucherMutation,
  usePostJournalVoucherMutation,
  useGetFinancialStatementsQuery,
  useGetGLAccountsQuery,
  useGetFiscalPeriodsQuery,
} = financeApi;
```

---

## 6. ONE-CLICK REPORT GENERATOR COMPONENT

### 6.1 Financial Statement Generator Page

**File: `frontend/src/features/reports/FinancialStatementGenerator.tsx`**

```typescript
import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Stack,
  Chip,
} from '@mui/material';
import {
  Download as DownloadIcon,
  PictureAsPdf as PdfIcon,
  TableChart as ExcelIcon,
  Assessment as ReportIcon,
} from '@mui/icons-material';
import { 
  useGetFinancialStatementsQuery,
  useGetFiscalPeriodsQuery 
} from '../../api/financeApi';
import ProfitLossStatement from './ProfitLossStatement';
import BalanceSheet from './BalanceSheet';
import CashFlowStatement from './CashFlowStatement';
import TrialBalance from './TrialBalance';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function FinancialStatementGenerator() {
  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [comparisonPeriod, setComparisonPeriod] = useState('');
  const [tabValue, setTabValue] = useState(0);

  // Fetch periods
  const { data: periods, isLoading: periodsLoading } = useGetFiscalPeriodsQuery({});

  // Fetch statements (only when period selected)
  const { 
    data: statements, 
    isLoading: statementsLoading,
    isError,
    error 
  } = useGetFinancialStatementsQuery(
    { 
      period: selectedPeriod,
      comparisonPeriod: comparisonPeriod || undefined,
      format: 'json'
    },
    { skip: !selectedPeriod }
  );

  const handleGenerateReport = () => {
    // Statements auto-fetch when period changes
    // This can trigger a refetch if needed
  };

  const handleDownloadPDF = async () => {
    if (!selectedPeriod) return;
    
    const response = await fetch(
      `${process.env.REACT_APP_API_URL}/finance/reports/financial-statements/?period=${selectedPeriod}&format=pdf`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      }
    );
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `financial_statements_${selectedPeriod}.pdf`;
    a.click();
  };

  const handleDownloadExcel = async () => {
    if (!selectedPeriod) return;
    
    const response = await fetch(
      `${process.env.REACT_APP_API_URL}/finance/reports/financial-statements/?period=${selectedPeriod}&format=excel`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      }
    );
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `financial_statements_${selectedPeriod}.xlsx`;
    a.click();
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          <ReportIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Financial Statement Generator
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Generate comprehensive financial statements with one click
        </Typography>
      </Box>

      {/* Configuration Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Period *</InputLabel>
                <Select
                  value={selectedPeriod}
                  onChange={(e) => setSelectedPeriod(e.target.value)}
                  label="Period *"
                >
                  {periods?.map((period) => (
                    <MenuItem key={period.id} value={period.id}>
                      {period.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Comparison Period (Optional)</InputLabel>
                <Select
                  value={comparisonPeriod}
                  onChange={(e) => setComparisonPeriod(e.target.value)}
                  label="Comparison Period (Optional)"
                >
                  <MenuItem value="">None</MenuItem>
                  {periods?.map((period) => (
                    <MenuItem key={period.id} value={period.id}>
                      {period.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <Stack direction="row" spacing={2}>
                <Button
                  variant="contained"
                  fullWidth
                  onClick={handleGenerateReport}
                  disabled={!selectedPeriod || statementsLoading}
                  startIcon={statementsLoading ? <CircularProgress size={20} /> : <ReportIcon />}
                >
                  {statementsLoading ? 'Generating...' : 'Generate'}
                </Button>
              </Stack>
            </Grid>
          </Grid>

          {/* Export buttons */}
          {statements && (
            <Box sx={{ mt: 2, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                startIcon={<PdfIcon />}
                onClick={handleDownloadPDF}
              >
                Download PDF
              </Button>
              <Button
                variant="outlined"
                startIcon={<ExcelIcon />}
                onClick={handleDownloadExcel}
              >
                Download Excel
              </Button>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Error handling */}
      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to generate financial statements. Please try again.
        </Alert>
      )}

      {/* Reports Display */}
      {statements && (
        <Card>
          <CardContent>
            {/* Metadata */}
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography variant="h6">{statements.metadata.company}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Period: {statements.metadata.period}
                </Typography>
              </Box>
              <Stack direction="row" spacing={1}>
                <Chip 
                  label={`Currency: ${statements.metadata.currency}`}
                  color="primary"
                  variant="outlined"
                />
                <Chip 
                  label={new Date(statements.metadata.generated_at).toLocaleString()}
                  variant="outlined"
                />
              </Stack>
            </Box>

            {/* Tabs for different statements */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
                <Tab label="Profit & Loss" />
                <Tab label="Balance Sheet" />
                <Tab label="Cash Flow" />
                <Tab label="Trial Balance" />
              </Tabs>
            </Box>

            <TabPanel value={tabValue} index={0}>
              <ProfitLossStatement data={statements.profit_loss} />
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <BalanceSheet data={statements.balance_sheet} />
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              <CashFlowStatement data={statements.cash_flow} />
            </TabPanel>

            <TabPanel value={tabValue} index={3}>
              <TrialBalance data={statements.trial_balance} />
            </TabPanel>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
```

### 6.2 Profit & Loss Statement Component

**File: `frontend/src/features/reports/ProfitLossStatement.tsx`**

```typescript
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Divider,
} from '@mui/material';
import { formatCurrency, formatPercentage } from '../../utils/formatters';

interface ProfitLossProps {
  data: any;
}

export default function ProfitLossStatement({ data }: ProfitLossProps) {
  const renderSection = (title: string, items: any[], total: number, level = 0) => (
    <>
      <TableRow>
        <TableCell 
          colSpan={2}
          sx={{ 
            fontWeight: 'bold', 
            fontSize: level === 0 ? '1.1rem' : '1rem',
            backgroundColor: level === 0 ? '#f5f5f5' : 'transparent',
            paddingLeft: `${level * 20 + 16}px`
          }}
        >
          {title}
        </TableCell>
      </TableRow>
      {items.map((item, index) => (
        <TableRow key={index} hover>
          <TableCell sx={{ paddingLeft: `${(level + 1) * 20 + 16}px` }}>
            {item.account_code} - {item.account_name}
          </TableCell>
          <TableCell align="right">
            {formatCurrency(item.amount)}
          </TableCell>
        </TableRow>
      ))}
      <TableRow>
        <TableCell 
          sx={{ 
            fontWeight: 'bold', 
            paddingLeft: `${level * 20 + 16}px`,
            borderTop: '2px solid #ddd'
          }}
        >
          {`Total ${title}`}
        </TableCell>
        <TableCell 
          align="right" 
          sx={{ 
            fontWeight: 'bold',
            borderTop: '2px solid #ddd'
          }}
        >
          {formatCurrency(total)}
        </TableCell>
      </TableRow>
    </>
  );

  return (
    <Box>
      <Typography variant="h5" gutterBottom align="center" sx={{ mb: 3 }}>
        {data.title}
      </Typography>

      <TableContainer component={Paper} elevation={0} variant="outlined">
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#1976d2' }}>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>
                Description
              </TableCell>
              <TableCell align="right" sx={{ color: 'white', fontWeight: 'bold' }}>
                Amount
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Revenue */}
            {renderSection(
              'Revenue',
              data.sections.revenue.items,
              data.sections.revenue.total,
              0
            )}

            <TableRow>
              <TableCell colSpan={2}><Divider /></TableCell>
            </TableRow>

            {/* Cost of Sales */}
            {renderSection(
              'Cost of Sales',
              data.sections.cost_of_sales.items,
              data.sections.cost_of_sales.total,
              0
            )}

            {/* Gross Profit */}
            <TableRow>
              <TableCell colSpan={2}><Divider sx={{ borderWidth: 2 }} /></TableCell>
            </TableRow>
            <TableRow sx={{ backgroundColor: '#e3f2fd' }}>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
                GROSS PROFIT
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
                {formatCurrency(data.sections.gross_profit.amount)}
                <Typography variant="caption" display="block" color="text.secondary">
                  {formatPercentage(data.sections.gross_profit.percentage)} margin
                </Typography>
              </TableCell>
            </TableRow>

            <TableRow>
              <TableCell colSpan={2}><Divider /></TableCell>
            </TableRow>

            {/* Operating Expenses */}
            {renderSection(
              'Operating Expenses',
              data.sections.expenses.items,
              data.sections.expenses.total,
              0
            )}

            {/* Operating Profit */}
            <TableRow sx={{ backgroundColor: '#fff9c4' }}>
              <TableCell sx={{ fontWeight: 'bold' }}>
                OPERATING PROFIT
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                {formatCurrency(data.sections.operating_profit.amount)}
              </TableCell>
            </TableRow>

            <TableRow>
              <TableCell colSpan={2}><Divider /></TableCell>
            </TableRow>

            {/* Other Income & Expenses */}
            {renderSection(
              'Other Income',
              data.sections.other_income.items,
              data.sections.other_income.total,
              0
            )}
            {renderSection(
              'Other Expenses',
              data.sections.other_expenses.items,
              data.sections.other_expenses.total,
              0
            )}

            {/* Net Profit */}
            <TableRow>
              <TableCell colSpan={2}><Divider sx={{ borderWidth: 3, borderColor: '#1976d2' }} /></TableCell>
            </TableRow>
            <TableRow sx={{ backgroundColor: '#c8e6c9' }}>
              <TableCell sx={{ fontWeight: 'bold', fontSize: '1.2rem' }}>
                NET PROFIT
              </TableCell>
              <TableCell align="right" sx={{ fontWeight: 'bold', fontSize: '1.2rem' }}>
                {formatCurrency(data.sections.net_profit.amount)}
                <Typography variant="caption" display="block" color="text.secondary">
                  {formatPercentage(data.sections.net_profit.percentage)} net margin
                </Typography>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
```

---

## 7. JOURNAL VOUCHER MANAGEMENT

### 7.1 Journal Voucher List

**File: `frontend/src/features/journal-entries/JournalVoucherList.tsx`**

```typescript
import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Button,
  Typography,
  TextField,
  MenuItem,
  Stack,
  Chip,
  IconButton,
  Dialog,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Visibility as ViewIcon,
  Send as SendIcon,
  CheckCircle as ApproveIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import { useNavigate } from 'react-router-dom';
import { 
  useGetJournalVouchersQuery,
  useSubmitJournalVoucherMutation,
  useApproveJournalVoucherMutation 
} from '../../api/financeApi';
import { formatCurrency, formatDate } from '../../utils/formatters';
import JournalVoucherDetail from './JournalVoucherDetail';

const statusColors = {
  'DRAFT': 'default',
  'IN_REVIEW': 'info',
  'APPROVED': 'success',
  'POSTED': 'primary',
  'REJECTED': 'error',
};

export default function JournalVoucherList() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState('');
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedJV, setSelectedJV] = useState(null);

  const { data: jvs, isLoading } = useGetJournalVouchersQuery({ 
    status: statusFilter || undefined 
  });

  const [submitJV] = useSubmitJournalVoucherMutation();
  const [approveJV] = useApproveJournalVoucherMutation();

  const columns: GridColDef[] = [
    {
      field: 'voucher_number',
      headerName: 'Voucher #',
      width: 150,
      renderCell: (params) => (
        <Typography 
          variant="body2" 
          sx={{ fontWeight: 'medium', cursor: 'pointer' }}
          onClick={() => {
            setSelectedJV(params.row);
            setDetailOpen(true);
          }}
        >
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'voucher_date',
      headerName: 'Date',
      width: 120,
      valueFormatter: (params) => formatDate(params.value),
    },
    {
      field: 'description',
      headerName: 'Description',
      flex: 1,
      minWidth: 200,
    },
    {
      field: 'total_amount',
      headerName: 'Amount',
      width: 150,
      align: 'right',
      renderCell: (params) => formatCurrency(params.row.total_debit),
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 130,
      renderCell: (params) => (
        <Chip 
          label={params.value.replace('_', ' ')} 
          color={statusColors[params.value] as any}
          size="small"
        />
      ),
    },
    {
      field: 'via_ai',
      headerName: 'AI',
      width: 80,
      renderCell: (params) => (
        params.value ? <Chip label="AI" size="small" color="secondary" /> : null
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params) => {
        const actions = [
          <GridActionsCellItem
            icon={<ViewIcon />}
            label="View"
            onClick={() => {
              setSelectedJV(params.row);
              setDetailOpen(true);
            }}
          />,
        ];

        if (params.row.status === 'DRAFT') {
          actions.push(
            <GridActionsCellItem
              icon={<SendIcon />}
              label="Submit"
              onClick={() => handleSubmit(params.row.id)}
            />
          );
        }

        if (params.row.status === 'IN_REVIEW' && params.row.can_approve) {
          actions.push(
            <GridActionsCellItem
              icon={<ApproveIcon />}
              label="Approve"
              onClick={() => handleApprove(params.row.id)}
            />
          );
        }

        return actions;
      },
    },
  ];

  const handleSubmit = async (id: string) => {
    try {
      await submitJV(id).unwrap();
      // Show success notification
    } catch (error) {
      // Show error notification
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await approveJV(id).unwrap();
      // Show success notification
    } catch (error) {
      // Show error notification
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Journal Vouchers</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/finance/journal-entries/new')}
        >
          New Journal Entry
        </Button>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2}>
            <TextField
              select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              sx={{ minWidth: 200 }}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="DRAFT">Draft</MenuItem>
              <MenuItem value="IN_REVIEW">In Review</MenuItem>
              <MenuItem value="APPROVED">Approved</MenuItem>
              <MenuItem value="POSTED">Posted</MenuItem>
              <MenuItem value="REJECTED">Rejected</MenuItem>
            </TextField>
          </Stack>
        </CardContent>
      </Card>

      {/* Data Grid */}
      <Card>
        <DataGrid
          rows={jvs || []}
          columns={columns}
          loading={isLoading}
          autoHeight
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          disableRowSelectionOnClick
        />
      </Card>

      {/* Detail Dialog */}
      <Dialog 
        open={detailOpen} 
        onClose={() => setDetailOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        {selectedJV && (
          <JournalVoucherDetail 
            jvId={selectedJV.id} 
            onClose={() => setDetailOpen(false)}
          />
        )}
      </Dialog>
    </Box>
  );
}
```

### 7.2 Journal Voucher Creation Form

**File: `frontend/src/features/journal-entries/JournalVoucherForm.tsx`**

```typescript
import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  TextField,
  Button,
  Typography,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Autocomplete,
  Stack,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import { useForm, useFieldArray, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import {
  useGetGLAccountsQuery,
  useGetFiscalPeriodsQuery,
  useCreateJournalVoucherMutation,
  useSubmitJournalVoucherMutation,
} from '../../api/financeApi';
import { formatCurrency } from '../../utils/formatters';

interface JVFormData {
  voucher_date: string;
  description: string;
  reference: string;
  period_id: string;
  lines: {
    account_id: string;
    debit: number;
    credit: number;
    description: string;
  }[];
}

export default function JournalVoucherForm() {
  const navigate = useNavigate();
  const { data: accounts } = useGetGLAccountsQuery();
  const { data: periods } = useGetFiscalPeriodsQuery({ status: 'OPEN' });
  
  const [createJV] = useCreateJournalVoucherMutation();
  const [submitJV] = useSubmitJournalVoucherMutation();

  const { control, handleSubmit, watch, formState: { errors } } = useForm<JVFormData>({
    defaultValues: {
      voucher_date: new Date().toISOString().split('T')[0],
      description: '',
      reference: '',
      period_id: '',
      lines: [
        { account_id: '', debit: 0, credit: 0, description: '' },
        { account_id: '', debit: 0, credit: 0, description: '' },
      ],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'lines',
  });

  const lines = watch('lines');
  
  // Calculate totals
  const totalDebit = lines.reduce((sum, line) => sum + (Number(line.debit) || 0), 0);
  const totalCredit = lines.reduce((sum, line) => sum + (Number(line.credit) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  const onSubmit = async (data: JVFormData, shouldSubmit = false) => {
    try {
      const result = await createJV(data).unwrap();
      
      if (shouldSubmit) {
        await submitJV(result.id).unwrap();
      }
      
      navigate('/finance/journal-entries');
    } catch (error) {
      console.error('Failed to create JV:', error);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        New Journal Entry
      </Typography>

      <form>
        {/* Header Section */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={3}>
              <Grid item xs={12} md={3}>
                <Controller
                  name="voucher_date"
                  control={control}
                  rules={{ required: 'Date is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Voucher Date"
                      type="date"
                      fullWidth
                      required
                      error={!!errors.voucher_date}
                      helperText={errors.voucher_date?.message}
                      InputLabelProps={{ shrink: true }}
                    />
                  )}
                />
              </Grid>

              <Grid item xs={12} md={3}>
                <Controller
                  name="period_id"
                  control={control}
                  rules={{ required: 'Period is required' }}
                  render={({ field }) => (
                    <Autocomplete
                      {...field}
                      options={periods || []}
                      getOptionLabel={(option) => option.name}
                      onChange={(_, value) => field.onChange(value?.id)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Period"
                          required
                          error={!!errors.period_id}
                          helperText={errors.period_id?.message}
                        />
                      )}
                    />
                  )}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Controller
                  name="reference"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Reference"
                      fullWidth
                    />
                  )}
                />
              </Grid>

              <Grid item xs={12}>
                <Controller
                  name="description"
                  control={control}
                  rules={{ required: 'Description is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Description"
                      fullWidth
                      required
                      multiline
                      rows={2}
                      error={!!errors.description}
                      helperText={errors.description?.message}
                    />
                  )}
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Lines Section */}
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">Journal Lines</Typography>
              <Button
                startIcon={<AddIcon />}
                onClick={() => append({ account_id: '', debit: 0, credit: 0, description: '' })}
              >
                Add Line
              </Button>
            </Box>

            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Account</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell align="right">Debit</TableCell>
                  <TableCell align="right">Credit</TableCell>
                  <TableCell width={50}></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {fields.map((field, index) => (
                  <TableRow key={field.id}>
                    <TableCell>
                      <Controller
                        name={`lines.${index}.account_id`}
                        control={control}
                        rules={{ required: 'Account is required' }}
                        render={({ field }) => (
                          <Autocomplete
                            {...field}
                            options={accounts || []}
                            getOptionLabel={(option) => 
                              `${option.code} - ${option.name}`
                            }
                            onChange={(_, value) => field.onChange(value?.id)}
                            sx={{ minWidth: 300 }}
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                size="small"
                                error={!!errors.lines?.[index]?.account_id}
                              />
                            )}
                          />
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Controller
                        name={`lines.${index}.description`}
                        control={control}
                        render={({ field }) => (
                          <TextField {...field} size="small" fullWidth />
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Controller
                        name={`lines.${index}.debit`}
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            type="number"
                            size="small"
                            sx={{ width: 150 }}
                            inputProps={{ step: 0.01, min: 0 }}
                          />
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Controller
                        name={`lines.${index}.credit`}
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            type="number"
                            size="small"
                            sx={{ width: 150 }}
                            inputProps={{ step: 0.01, min: 0 }}
                          />
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton
                        onClick={() => remove(index)}
                        disabled={fields.length <= 2}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
                
                {/* Totals Row */}
                <TableRow>
                  <TableCell colSpan={2} align="right">
                    <Typography variant="subtitle1" fontWeight="bold">
                      TOTALS:
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography 
                      variant="subtitle1" 
                      fontWeight="bold"
                      color={isBalanced ? 'success.main' : 'error.main'}
                    >
                      {formatCurrency(totalDebit)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography 
                      variant="subtitle1" 
                      fontWeight="bold"
                      color={isBalanced ? 'success.main' : 'error.main'}
                    >
                      {formatCurrency(totalCredit)}
                    </Typography>
                  </TableCell>
                  <TableCell />
                </TableRow>
              </TableBody>
            </Table>

            {/* Balance indicator */}
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              {isBalanced ? (
                <Typography color="success.main" variant="body1">
                  ✓ Journal entry is balanced
                </Typography>
              ) : (
                <Typography color="error" variant="body1">
                  ✗ Debits and credits must be equal (Difference: {formatCurrency(Math.abs(totalDebit - totalCredit))})
                </Typography>
              )}
            </Box>

            {/* Action Buttons */}
            <Stack direction="row" spacing={2} sx={{ mt: 3 }} justifyContent="flex-end">
              <Button
                variant="outlined"
                onClick={() => navigate('/finance/journal-entries')}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                color="secondary"
                startIcon={<SaveIcon />}
                onClick={handleSubmit((data) => onSubmit(data, false))}
                disabled={!isBalanced}
              >
                Save as Draft
              </Button>
              <Button
                variant="contained"
                startIcon={<SendIcon />}
                onClick={handleSubmit((data) => onSubmit(data, true))}
                disabled={!isBalanced}
              >
                Save & Submit
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </form>
    </Box>
  );
}
```

This is Part 4. Let me now copy all these files to the outputs directory and create a final summary document:

