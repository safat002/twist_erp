import api from './api';

export const fetchAccounts = (params = {}) =>
  api.get('/api/v1/finance/accounts/', { params });

export const fetchInventoryPostingRules = (params = {}) =>
  api.get('/api/v1/finance/inventory-posting-rules/', { params });

export const createInventoryPostingRule = (payload) =>
  api.post('/api/v1/finance/inventory-posting-rules/', payload);

export const updateInventoryPostingRule = (id, payload) =>
  api.put(`/api/v1/finance/inventory-posting-rules/${id}/`, payload);

export const deleteInventoryPostingRule = (id) =>
  api.delete(`/api/v1/finance/inventory-posting-rules/${id}/`);

export const createAccount = (payload) => api.post('/api/v1/finance/accounts/', payload);

export const updateAccount = (id, payload) =>
  api.put(`/api/v1/finance/accounts/${id}/`, payload);

export const deleteAccount = (id) => api.delete(`/api/v1/finance/accounts/${id}/`);

export const fetchJournals = () => api.get('/api/v1/finance/journals/');

export const fetchJournalVouchers = (params = {}) =>
  api.get('/api/v1/finance/journal-vouchers/', { params });

export const createJournalVoucher = (payload) =>
  api.post('/api/v1/finance/journal-vouchers/', payload);

export const updateJournalVoucher = (id, payload) =>
  api.put(`/api/v1/finance/journal-vouchers/${id}/`, payload);

export const deleteJournalVoucher = (id) =>
  api.delete(`/api/v1/finance/journal-vouchers/${id}/`);

export const postJournalVoucher = (id) =>
  api.post(`/api/v1/finance/journal-vouchers/${id}/post/`);

export const submitJournalVoucher = (id) =>
  api.post(`/api/v1/finance/journal-vouchers/${id}/submit/`);

export const approveJournalVoucher = (id) =>
  api.post(`/api/v1/finance/journal-vouchers/${id}/approve/`);

export const processJournalVoucherDocument = (formData) =>
  api.post('/api/v1/finance/journal-vouchers/process-document/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

export const fetchInvoices = (params = {}) =>
  api.get('/api/v1/finance/invoices/', { params });

export const createInvoice = (payload) => api.post('/api/v1/finance/invoices/', payload);

export const updateInvoice = (id, payload) =>
  api.put(`/api/v1/finance/invoices/${id}/`, payload);

export const postInvoice = (id) => api.post(`/api/v1/finance/invoices/${id}/post/`);

export const approveInvoice = (id) => api.post(`/api/v1/finance/invoices/${id}/approve/`);

export const fetchPayments = (params = {}) =>
  api.get('/api/v1/finance/payments/', { params });

export const createPayment = (payload) => api.post('/api/v1/finance/payments/', payload);

export const updatePayment = (id, payload) =>
  api.put(`/api/v1/finance/payments/${id}/`, payload);

export const postPayment = (id) => api.post(`/api/v1/finance/payments/${id}/post/`);

export const approvePayment = (id) => api.post(`/api/v1/finance/payments/${id}/approve/`);

// Fiscal Periods
export const fetchPeriods = (params = {}) => api.get('/api/v1/finance/periods/', { params });
export const createPeriod = (payload) => api.post('/api/v1/finance/periods/', payload);
export const updatePeriod = (id, payload) => api.put(`/api/v1/finance/periods/${id}/`, payload);
export const closePeriod = (id) => api.post(`/api/v1/finance/periods/${id}/close/`);
export const openPeriod = (id) => api.post(`/api/v1/finance/periods/${id}/open/`);
export const lockPeriod = (id) => api.post(`/api/v1/finance/periods/${id}/lock/`);
export const unlockPeriod = (id) => api.post(`/api/v1/finance/periods/${id}/unlock/`);

// Bank Reconciliation
export const fetchBankStatements = (params = {}) => api.get('/api/v1/finance/bank-statements/', { params });
export const createBankStatement = (payload) => api.post('/api/v1/finance/bank-statements/', payload);
export const matchStatementLine = (id, payload) => api.post(`/api/v1/finance/bank-statements/${id}/match-line/`, payload);

// Finance Reports
export const getTrialBalance = (params = {}) =>
  api.get('/api/v1/finance/reports/trial-balance', { params });

export const getGeneralLedger = (params = {}) =>
  api.get('/api/v1/finance/reports/general-ledger', { params });

export const getARAging = (params = {}) =>
  api.get('/api/v1/finance/reports/ar-aging', { params });

export const getAPAging = (params = {}) =>
  api.get('/api/v1/finance/reports/ap-aging', { params });

export const getVATReturn = (params = {}) =>
  api.get('/api/v1/finance/reports/vat-return', { params });

// Currencies (multi-currency management)
export const fetchCurrencies = () => api.get('/api/v1/finance/currencies/');
export const createCurrency = (payload) => api.post('/api/v1/finance/currencies/', payload);
export const updateCurrency = (id, payload) => api.put(`/api/v1/finance/currencies/${id}/`, payload);
export const deleteCurrency = (id) => api.delete(`/api/v1/finance/currencies/${id}/`);
export const setBaseCurrency = (code) => api.post('/api/v1/finance/currencies/set-base/', { code });
export const fetchCurrencyChoices = () => api.get('/api/v1/companies/currency-choices/');
