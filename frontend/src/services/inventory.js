import api from './api';

export const fetchStockMovements = (params = {}) =>
  api.get('/api/v1/inventory/movements/', { params });

export const previewStockMovement = (movementId) =>
  api.get(`/api/v1/inventory/stock-movements/${movementId}/gl-preview/`);

export const createStockMovement = (payload) =>
  api.post('/api/v1/inventory/stock-movements/', payload);

export const createStockMovementLine = (payload) =>
  api.post('/api/v1/inventory/stock-movement-lines/', payload);

export const confirmStockMovementReceipt = (movementId, payload = {}) =>
  api.post(`/api/v1/inventory/stock-movements/${movementId}/confirm_receipt/`, payload);
