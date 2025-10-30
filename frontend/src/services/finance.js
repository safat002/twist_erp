import api from './api';

export const fetchAccounts = (params = {}) =>
  api.get('/api/v1/finance/accounts/', { params });

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

export const fetchInvoices = (params = {}) =>
  api.get('/api/v1/finance/invoices/', { params });

export const createInvoice = (payload) => api.post('/api/v1/finance/invoices/', payload);

export const updateInvoice = (id, payload) =>
  api.put(`/api/v1/finance/invoices/${id}/`, payload);

export const postInvoice = (id) => api.post(`/api/v1/finance/invoices/${id}/post/`);

export const fetchPayments = (params = {}) =>
  api.get('/api/v1/finance/payments/', { params });

export const createPayment = (payload) => api.post('/api/v1/finance/payments/', payload);

export const updatePayment = (id, payload) =>
  api.put(`/api/v1/finance/payments/${id}/`, payload);

export const postPayment = (id) => api.post(`/api/v1/finance/payments/${id}/post/`);
