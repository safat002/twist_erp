/**
 * Return To Vendor (RTV) Service
 * API client for supplier return management
 */

import api from './api';

// ============================================================================
// CRUD Operations
// ============================================================================

/**
 * Fetch all RTVs
 */
export const fetchRTVs = (params = {}) =>
  api.get('/api/v1/inventory/return-to-vendor/', { params });

/**
 * Get a single RTV by ID
 */
export const getRTV = (id) =>
  api.get(`/api/v1/inventory/return-to-vendor/${id}/`);

/**
 * Create a new RTV
 */
export const createRTV = (data) =>
  api.post('/api/v1/inventory/return-to-vendor/', data);

/**
 * Update an existing RTV
 */
export const updateRTV = (id, data) =>
  api.patch(`/api/v1/inventory/return-to-vendor/${id}/`, data);

/**
 * Delete an RTV
 */
export const deleteRTV = (id) =>
  api.delete(`/api/v1/inventory/return-to-vendor/${id}/`);

// ============================================================================
// Workflow Actions
// ============================================================================

/**
 * Submit RTV for approval
 */
export const submitRTV = (id) =>
  api.post(`/api/v1/inventory/return-to-vendor/${id}/submit/`);

/**
 * Approve RTV (creates negative movement events)
 */
export const approveRTV = (id) =>
  api.post(`/api/v1/inventory/return-to-vendor/${id}/approve/`);

/**
 * Complete RTV (reverses budget and posts to GL)
 */
export const completeRTV = (id, data) =>
  api.post(`/api/v1/inventory/return-to-vendor/${id}/complete/`, data);

/**
 * Update shipping information
 */
export const updateShipping = (id, shippingData) =>
  api.post(`/api/v1/inventory/return-to-vendor/${id}/update_shipping/`, shippingData);

/**
 * Cancel RTV
 */
export const cancelRTV = (id, reason) =>
  api.post(`/api/v1/inventory/return-to-vendor/${id}/cancel/`, { reason });

/**
 * Get RTV summary
 */
export const getRTVSummary = (id) =>
  api.get(`/api/v1/inventory/return-to-vendor/${id}/summary/`);

// ============================================================================
// RTV Lines Management
// ============================================================================

/**
 * Fetch RTV lines
 */
export const fetchRTVLines = (rtvId) =>
  api.get('/api/v1/inventory/return-to-vendor-lines/', {
    params: { rtv: rtvId }
  });

/**
 * Create RTV line
 */
export const createRTVLine = (data) =>
  api.post('/api/v1/inventory/return-to-vendor-lines/', data);

/**
 * Update RTV line
 */
export const updateRTVLine = (id, data) =>
  api.patch(`/api/v1/inventory/return-to-vendor-lines/${id}/`, data);

/**
 * Delete RTV line
 */
export const deleteRTVLine = (id) =>
  api.delete(`/api/v1/inventory/return-to-vendor-lines/${id}/`);

// ============================================================================
// Constants
// ============================================================================

export const RTV_STATUS = {
  DRAFT: 'DRAFT',
  SUBMITTED: 'SUBMITTED',
  APPROVED: 'APPROVED',
  IN_TRANSIT: 'IN_TRANSIT',
  COMPLETED: 'COMPLETED',
  CANCELLED: 'CANCELLED',
};

export const RTV_STATUS_LABELS = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted for Approval',
  APPROVED: 'Approved',
  IN_TRANSIT: 'In Transit to Vendor',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
};

export const RTV_STATUS_COLORS = {
  DRAFT: 'default',
  SUBMITTED: 'info',
  APPROVED: 'success',
  IN_TRANSIT: 'warning',
  COMPLETED: 'primary',
  CANCELLED: 'error',
};

export const RETURN_REASONS = {
  DEFECTIVE: 'DEFECTIVE',
  WRONG_ITEM: 'WRONG_ITEM',
  EXCESS_QUANTITY: 'EXCESS_QUANTITY',
  QUALITY_ISSUE: 'QUALITY_ISSUE',
  EXPIRED: 'EXPIRED',
  DAMAGED_IN_TRANSIT: 'DAMAGED_IN_TRANSIT',
  NOT_AS_ORDERED: 'NOT_AS_ORDERED',
  OTHER: 'OTHER',
};

export const RETURN_REASON_LABELS = {
  DEFECTIVE: 'Defective/Damaged Goods',
  WRONG_ITEM: 'Wrong Item Received',
  EXCESS_QUANTITY: 'Excess Quantity Received',
  QUALITY_ISSUE: 'Quality Issue',
  EXPIRED: 'Expired/Near Expiry',
  DAMAGED_IN_TRANSIT: 'Damaged in Transit',
  NOT_AS_ORDERED: 'Not as Ordered',
  OTHER: 'Other',
};

export const REFUND_STATUS = {
  PENDING: 'PENDING',
  RECEIVED: 'RECEIVED',
  NOT_APPLICABLE: 'NOT_APPLICABLE',
};

export const REFUND_STATUS_LABELS = {
  PENDING: 'Pending',
  RECEIVED: 'Received',
  NOT_APPLICABLE: 'Not Applicable',
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format RTV number for display
 */
export const formatRTVNumber = (rtv) => {
  return rtv.rtv_number || 'N/A';
};

/**
 * Get status badge color
 */
export const getStatusColor = (status) => {
  return RTV_STATUS_COLORS[status] || 'default';
};

/**
 * Get status label
 */
export const getStatusLabel = (status) => {
  return RTV_STATUS_LABELS[status] || status;
};

/**
 * Get return reason label
 */
export const getReturnReasonLabel = (reason) => {
  return RETURN_REASON_LABELS[reason] || reason;
};

/**
 * Check if RTV can be edited
 */
export const canEditRTV = (rtv) => {
  return rtv.can_edit || rtv.status === 'DRAFT';
};

/**
 * Check if RTV can be submitted
 */
export const canSubmitRTV = (rtv) => {
  return rtv.can_submit || rtv.status === 'DRAFT';
};

/**
 * Check if RTV can be approved
 */
export const canApproveRTV = (rtv) => {
  return rtv.can_approve || rtv.status === 'SUBMITTED';
};

/**
 * Check if RTV can be completed
 */
export const canCompleteRTV = (rtv) => {
  return rtv.can_complete || rtv.status === 'APPROVED' || rtv.status === 'IN_TRANSIT';
};

/**
 * Calculate line total
 */
export const calculateLineTotal = (quantity, unitCost) => {
  const qty = parseFloat(quantity || 0);
  const cost = parseFloat(unitCost || 0);
  return qty * cost;
};

/**
 * Calculate RTV total
 */
export const calculateRTVTotal = (lines) => {
  return lines.reduce((total, line) => {
    return total + calculateLineTotal(line.quantity_to_return, line.unit_cost);
  }, 0);
};

/**
 * Format currency amount
 */
export const formatAmount = (amount, currency = 'USD') => {
  const num = parseFloat(amount || 0);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(num);
};

/**
 * Validate RTV data
 */
export const validateRTVData = (data) => {
  const errors = {};

  if (!data.rtv_date) {
    errors.rtv_date = 'RTV date is required';
  }

  if (!data.goods_receipt) {
    errors.goods_receipt = 'Goods receipt is required';
  }

  if (!data.supplier_id) {
    errors.supplier_id = 'Supplier is required';
  }

  if (!data.return_reason) {
    errors.return_reason = 'Return reason is required';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
};

/**
 * Validate RTV line data
 */
export const validateRTVLineData = (data) => {
  const errors = {};

  if (!data.product) {
    errors.product = 'Product is required';
  }

  if (!data.quantity_to_return || parseFloat(data.quantity_to_return) <= 0) {
    errors.quantity_to_return = 'Quantity must be greater than zero';
  }

  if (!data.unit_cost || parseFloat(data.unit_cost) < 0) {
    errors.unit_cost = 'Unit cost cannot be negative';
  }

  if (!data.uom) {
    errors.uom = 'Unit of measure is required';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
};

/**
 * Format shipping status
 */
export const formatShippingStatus = (rtv) => {
  if (!rtv.carrier || !rtv.tracking_number) {
    return 'Not Shipped';
  }

  if (rtv.delivered_to_vendor_date) {
    return `Delivered on ${new Date(rtv.delivered_to_vendor_date).toLocaleDateString()}`;
  }

  if (rtv.actual_pickup_date) {
    return `Picked up on ${new Date(rtv.actual_pickup_date).toLocaleDateString()}`;
  }

  if (rtv.pickup_date) {
    return `Scheduled for ${new Date(rtv.pickup_date).toLocaleDateString()}`;
  }

  return 'Pending Pickup';
};

/**
 * Get refund status color
 */
export const getRefundStatusColor = (refundStatus) => {
  const colors = {
    PENDING: 'warning',
    RECEIVED: 'success',
    NOT_APPLICABLE: 'default',
  };
  return colors[refundStatus] || 'default';
};

/**
 * Check if budget was reversed
 */
export const isBudgetReversed = (lines) => {
  if (!lines || lines.length === 0) return false;
  return lines.every(line => !line.budget_item || line.budget_reversed);
};

export default {
  fetchRTVs,
  getRTV,
  createRTV,
  updateRTV,
  deleteRTV,
  submitRTV,
  approveRTV,
  completeRTV,
  updateShipping,
  cancelRTV,
  getRTVSummary,
  fetchRTVLines,
  createRTVLine,
  updateRTVLine,
  deleteRTVLine,
  RTV_STATUS,
  RTV_STATUS_LABELS,
  RTV_STATUS_COLORS,
  RETURN_REASONS,
  RETURN_REASON_LABELS,
  REFUND_STATUS,
  REFUND_STATUS_LABELS,
  formatRTVNumber,
  getStatusColor,
  getStatusLabel,
  getReturnReasonLabel,
  canEditRTV,
  canSubmitRTV,
  canApproveRTV,
  canCompleteRTV,
  calculateLineTotal,
  calculateRTVTotal,
  formatAmount,
  validateRTVData,
  validateRTVLineData,
  formatShippingStatus,
  getRefundStatusColor,
  isBudgetReversed,
};
