import api from './api';

export const getMaterialIssues = (params = {}) =>
  api.get('/api/v1/inventory/material-issues/', { params });

export const getMaterialIssue = (id) =>
  api.get(`/api/v1/inventory/material-issues/${id}/`);

export const createMaterialIssue = (payload) =>
  api.post('/api/v1/inventory/material-issues/', payload);

export const updateMaterialIssue = (id, payload) =>
  api.put(`/api/v1/inventory/material-issues/${id}/`, payload);

export const submitMaterialIssue = (id) =>
  api.post(`/api/v1/inventory/material-issues/${id}/submit/`);

export const approveMaterialIssue = (id) =>
  api.post(`/api/v1/inventory/material-issues/${id}/approve/`);

export const issueMaterial = (id) =>
  api.post(`/api/v1/inventory/material-issues/${id}/issue/`);

export const cancelMaterialIssue = (id, payload = {}) =>
  api.post(`/api/v1/inventory/material-issues/${id}/cancel/`, payload);

export const getIssueSummary = (id) =>
  api.get(`/api/v1/inventory/material-issues/${id}/summary/`);

export const getAvailableBatches = (params = {}) =>
  api.get('/api/v1/inventory/material-issues/available_batches/', { params });

export const getAvailableSerials = (params = {}) =>
  api.get('/api/v1/inventory/material-issues/available_serials/', { params });

export const getInternalRequisitions = (params = {}) =>
  api.get('/api/v1/inventory/requisitions/internal/', { params });

export const getInternalRequisition = (id) =>
  api.get(`/api/v1/inventory/requisitions/internal/${id}/`);
