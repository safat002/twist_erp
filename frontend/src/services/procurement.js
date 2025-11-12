/**
 * Procurement Service
 * Handles Purchase Orders, Goods Receipts, and Supplier operations
 */

import api from './api';

// ============================================================================
// PURCHASE ORDERS
// ============================================================================

export const getPurchaseOrders = (params = {}) =>
  api.get('/api/v1/procurement/purchase-orders/', { params });

export const getPurchaseOrder = (id) =>
  api.get(`/api/v1/procurement/purchase-orders/${id}/`);

export const createPurchaseOrder = (data) =>
  api.post('/api/v1/procurement/purchase-orders/', data);

export const updatePurchaseOrder = (id, data) =>
  api.patch(`/api/v1/procurement/purchase-orders/${id}/`, data);

export const deletePurchaseOrder = (id) =>
  api.delete(`/api/v1/procurement/purchase-orders/${id}/`);

// ============================================================================
// GOODS RECEIPTS (GRN)
// ============================================================================

export const getGoodsReceipts = (params = {}) =>
  api.get('/api/v1/inventory/goods-receipts/', { params });

export const getGoodsReceipt = (id) =>
  api.get(`/api/v1/inventory/goods-receipts/${id}/`);

export const createGoodsReceipt = (data) =>
  api.post('/api/v1/inventory/goods-receipts/', data);

export const updateGoodsReceipt = (id, data) =>
  api.patch(`/api/v1/inventory/goods-receipts/${id}/`, data);

export const deleteGoodsReceipt = (id) =>
  api.delete(`/api/v1/inventory/goods-receipts/${id}/`);

export const postGoodsReceipt = (id) =>
  api.post(`/api/v1/inventory/goods-receipts/${id}/post/`);

export const placeGRNOnHold = (id, data) =>
  api.post(`/api/v1/inventory/goods-receipts/${id}/place_on_hold/`, data);

export const releaseGRNHold = (id, data) =>
  api.post(`/api/v1/inventory/goods-receipts/${id}/release_hold/`, data);

// ============================================================================
// SUPPLIERS
// ============================================================================

export const getSuppliers = (params = {}) =>
  api.get('/api/v1/procurement/suppliers/', { params });

export const getSupplier = (id) =>
  api.get(`/api/v1/procurement/suppliers/${id}/`);

export const createSupplier = (data) =>
  api.post('/api/v1/procurement/suppliers/', data);

export const updateSupplier = (id, data) =>
  api.patch(`/api/v1/procurement/suppliers/${id}/`, data);

export const deleteSupplier = (id) =>
  api.delete(`/api/v1/procurement/suppliers/${id}/`);

// ============================================================================
// CONSTANTS & ENUMS
// ============================================================================

export const PO_STATUSES = {
  DRAFT: 'DRAFT',
  SUBMITTED: 'SUBMITTED',
  APPROVED: 'APPROVED',
  ISSUED: 'ISSUED',
  PARTIALLY_RECEIVED: 'PARTIALLY_RECEIVED',
  RECEIVED: 'RECEIVED',
  CANCELLED: 'CANCELLED',
};

export const PO_STATUS_LABELS = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  APPROVED: 'Approved',
  ISSUED: 'Issued',
  PARTIALLY_RECEIVED: 'Partially Received',
  RECEIVED: 'Received',
  CANCELLED: 'Cancelled',
};

export const PO_STATUS_COLORS = {
  DRAFT: 'default',
  SUBMITTED: 'processing',
  APPROVED: 'success',
  ISSUED: 'purple',
  PARTIALLY_RECEIVED: 'orange',
  RECEIVED: 'blue',
  CANCELLED: 'red',
};

export const GRN_STATUSES = {
  DRAFT: 'DRAFT',
  POSTED: 'POSTED',
};

export const GRN_STATUS_LABELS = {
  DRAFT: 'Draft',
  POSTED: 'Posted',
};

export const GRN_STATUS_COLORS = {
  DRAFT: 'orange',
  POSTED: 'green',
};

export const QUALITY_STATUSES = {
  PENDING: 'pending',
  ON_HOLD: 'on_hold',
  PASSED: 'passed',
  REJECTED: 'rejected',
};

export const QUALITY_STATUS_LABELS = {
  pending: 'Pending QC',
  on_hold: 'On Hold',
  passed: 'Passed',
  rejected: 'Rejected',
};

export const QUALITY_STATUS_COLORS = {
  pending: 'orange',
  on_hold: 'red',
  passed: 'green',
  rejected: 'red',
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export const getPOStatusColor = (status) => {
  return PO_STATUS_COLORS[status] || 'default';
};

export const getPOStatusLabel = (status) => {
  return PO_STATUS_LABELS[status] || status;
};

export const getGRNStatusColor = (status) => {
  return GRN_STATUS_COLORS[status] || 'default';
};

export const getGRNStatusLabel = (status) => {
  return GRN_STATUS_LABELS[status] || status;
};

export const getQualityStatusColor = (status) => {
  return QUALITY_STATUS_COLORS[status] || 'default';
};

export const getQualityStatusLabel = (status) => {
  return QUALITY_STATUS_LABELS[status] || status;
};

export default {
  // Purchase Orders
  getPurchaseOrders,
  getPurchaseOrder,
  createPurchaseOrder,
  updatePurchaseOrder,
  deletePurchaseOrder,

  // Goods Receipts
  getGoodsReceipts,
  getGoodsReceipt,
  createGoodsReceipt,
  updateGoodsReceipt,
  deleteGoodsReceipt,
  postGoodsReceipt,
  placeGRNOnHold,
  releaseGRNHold,

  // Suppliers
  getSuppliers,
  getSupplier,
  createSupplier,
  updateSupplier,
  deleteSupplier,

  // Constants
  PO_STATUSES,
  PO_STATUS_LABELS,
  PO_STATUS_COLORS,
  GRN_STATUSES,
  GRN_STATUS_LABELS,
  GRN_STATUS_COLORS,
  QUALITY_STATUSES,
  QUALITY_STATUS_LABELS,
  QUALITY_STATUS_COLORS,

  // Helpers
  getPOStatusColor,
  getPOStatusLabel,
  getGRNStatusColor,
  getGRNStatusLabel,
  getQualityStatusColor,
  getQualityStatusLabel,
};
