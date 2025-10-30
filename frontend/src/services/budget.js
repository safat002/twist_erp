import api from './api';

export const fetchBudgetWorkspaceSummary = () => api.get('/api/v1/budgets/workspace/summary/');

export const fetchCostCenters = (params = {}) =>
  api.get('/api/v1/budgets/cost-centers/', { params });

export const createCostCenter = (payload) => api.post('/api/v1/budgets/cost-centers/', payload);

export const updateCostCenter = (id, payload) =>
  api.patch(`/api/v1/budgets/cost-centers/${id}/`, payload);

export const fetchBudgets = (params = {}) => api.get('/api/v1/budgets/periods/', { params });

export const createBudget = (payload) => api.post('/api/v1/budgets/periods/', payload);

export const updateBudget = (id, payload) =>
  api.patch(`/api/v1/budgets/periods/${id}/`, payload);

export const submitBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/submit/`);

export const approveBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/approve/`);

export const lockBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/lock/`);

export const closeBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/close/`);

export const recalculateBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/recalculate/`);

export const fetchBudgetLines = (params = {}) => api.get('/api/v1/budgets/lines/', { params });

export const createBudgetLine = (payload) => api.post('/api/v1/budgets/lines/', payload);

export const updateBudgetLine = (id, payload) =>
  api.patch(`/api/v1/budgets/lines/${id}/`, payload);

export const deleteBudgetLine = (id) => api.delete(`/api/v1/budgets/lines/${id}/`);

export const recordBudgetUsage = (payload) => api.post('/api/v1/budgets/usage/', payload);

export const fetchOverrides = (params = {}) => api.get('/api/v1/budgets/overrides/', { params });

export const createOverrideRequest = (payload) => api.post('/api/v1/budgets/overrides/', payload);

export const approveOverride = (id, notes) =>
  api.post(`/api/v1/budgets/overrides/${id}/approve/`, notes ? { notes } : {});

export const rejectOverride = (id, notes) =>
  api.post(`/api/v1/budgets/overrides/${id}/reject/`, notes ? { notes } : {});

export const checkBudgetAvailability = (payload) =>
  api.post('/api/v1/budgets/check-availability/', payload);

export const fetchBudgetSnapshots = (params = {}) =>
  api.get('/api/v1/budgets/snapshots/', { params });

export const createBudgetSnapshot = (payload) => api.post('/api/v1/budgets/snapshots/', payload);
