import api from './api';

export const fetchBOMs = (params = {}) => api.get('/api/v1/production/boms/', { params });

export const createBOM = (payload) => api.post('/api/v1/production/boms/', payload);

export const updateBOM = (id, payload) => api.put(`/api/v1/production/boms/${id}/`, payload);

export const deleteBOM = (id) => api.delete(`/api/v1/production/boms/${id}/`);

export const fetchWorkOrders = (params = {}) => api.get('/api/v1/production/work-orders/', { params });

export const createWorkOrder = (payload) => api.post('/api/v1/production/work-orders/', payload);

export const updateWorkOrder = (id, payload) =>
  api.put(`/api/v1/production/work-orders/${id}/`, payload);

export const releaseWorkOrder = (id) => api.post(`/api/v1/production/work-orders/${id}/release/`);

export const startWorkOrder = (id) => api.post(`/api/v1/production/work-orders/${id}/start/`);

export const completeWorkOrder = (id, payload) =>
  api.post(`/api/v1/production/work-orders/${id}/complete/`, payload);

export const issueMaterials = (id, payload) =>
  api.post(`/api/v1/production/work-orders/${id}/issue-materials/`, payload);

export const recordProductionReceipt = (id, payload) =>
  api.post(`/api/v1/production/work-orders/${id}/record-receipt/`, payload);

export const fetchMRPSummary = (params = {}) =>
  api.get('/api/v1/production/work-orders/mrp-summary/', { params });

export const fetchCapacitySummary = (params = {}) =>
  api.get('/api/v1/production/work-orders/capacity-summary/', { params });
