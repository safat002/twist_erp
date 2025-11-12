/**
 * Landed Cost Voucher Service
 * API client for landed cost voucher management
 */

import api from './api';

// ============================================================================
// CRUD Operations
// ============================================================================

/**
 * Fetch all landed cost vouchers
 */
export const fetchLandedCostVouchers = (params = {}) =>
  api.get('/api/v1/inventory/landed-cost-vouchers/', { params });

/**
 * Get a single voucher by ID
 */
export const getLandedCostVoucher = (id) =>
  api.get(`/api/v1/inventory/landed-cost-vouchers/${id}/`);

/**
 * Create a new landed cost voucher
 */
export const createLandedCostVoucher = (data) =>
  api.post('/api/v1/inventory/landed-cost-vouchers/', data);

/**
 * Update an existing voucher
 */
export const updateLandedCostVoucher = (id, data) =>
  api.patch(`/api/v1/inventory/landed-cost-vouchers/${id}/`, data);

/**
 * Delete a voucher
 */
export const deleteLandedCostVoucher = (id) =>
  api.delete(`/api/v1/inventory/landed-cost-vouchers/${id}/`);

// ============================================================================
// Workflow Actions
// ============================================================================

/**
 * Submit voucher for approval
 */
export const submitVoucher = (id) =>
  api.post(`/api/v1/inventory/landed-cost-vouchers/${id}/submit/`);

/**
 * Approve voucher
 */
export const approveVoucher = (id) =>
  api.post(`/api/v1/inventory/landed-cost-vouchers/${id}/approve/`);

/**
 * Cancel voucher
 */
export const cancelVoucher = (id, reason) =>
  api.post(`/api/v1/inventory/landed-cost-vouchers/${id}/cancel/`, { reason });

// ============================================================================
// Allocation Operations
// ============================================================================

/**
 * Generate allocation plan for a voucher
 */
export const generateAllocationPlan = (id, grnIds, apportionmentMethod = 'BY_VALUE') =>
  api.post(`/api/v1/inventory/landed-cost-vouchers/${id}/generate_allocation_plan/`, {
    goods_receipt_ids: grnIds,
    apportionment_method: apportionmentMethod
  });

/**
 * Allocate voucher to cost layers
 */
export const allocateVoucher = (id, allocationPlan) =>
  api.post(`/api/v1/inventory/landed-cost-vouchers/${id}/allocate/`, {
    allocation_plan: allocationPlan
  });

/**
 * Post voucher to GL
 */
export const postVoucherToGL = (id) =>
  api.post(`/api/v1/inventory/landed-cost-vouchers/${id}/post_to_gl/`);

/**
 * Get voucher summary
 */
export const getVoucherSummary = (id) =>
  api.get(`/api/v1/inventory/landed-cost-vouchers/${id}/summary/`);

// ============================================================================
// Allocation Management
// ============================================================================

/**
 * Fetch allocations for a voucher
 */
export const fetchAllocations = (voucherId) =>
  api.get('/api/v1/inventory/landed-cost-allocations/', {
    params: { voucher: voucherId }
  });

/**
 * Reverse an allocation
 */
export const reverseAllocation = (allocationId, reason) =>
  api.post(`/api/v1/inventory/landed-cost-allocations/${allocationId}/reverse/`, {
    reason
  });

// ============================================================================
// Constants
// ============================================================================

export const VOUCHER_STATUS = {
  DRAFT: 'DRAFT',
  SUBMITTED: 'SUBMITTED',
  APPROVED: 'APPROVED',
  ALLOCATED: 'ALLOCATED',
  POSTED: 'POSTED',
  CANCELLED: 'CANCELLED',
};

export const VOUCHER_STATUS_LABELS = {
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  APPROVED: 'Approved',
  ALLOCATED: 'Allocated to Cost Layers',
  POSTED: 'Posted to GL',
  CANCELLED: 'Cancelled',
};

export const VOUCHER_STATUS_COLORS = {
  DRAFT: 'default',
  SUBMITTED: 'info',
  APPROVED: 'success',
  ALLOCATED: 'secondary',
  POSTED: 'primary',
  CANCELLED: 'error',
};

export const APPORTIONMENT_METHODS = {
  BY_VALUE: 'BY_VALUE',
  BY_QUANTITY: 'BY_QUANTITY',
  EQUAL: 'EQUAL',
};

export const APPORTIONMENT_METHOD_LABELS = {
  BY_VALUE: 'By Value',
  BY_QUANTITY: 'By Quantity',
  EQUAL: 'Equal Distribution',
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format voucher number for display
 */
export const formatVoucherNumber = (voucher) => {
  return voucher.voucher_number || 'N/A';
};

/**
 * Get status badge color
 */
export const getStatusColor = (status) => {
  return VOUCHER_STATUS_COLORS[status] || 'default';
};

/**
 * Get status label
 */
export const getStatusLabel = (status) => {
  return VOUCHER_STATUS_LABELS[status] || status;
};

/**
 * Check if voucher can be edited
 */
export const canEditVoucher = (voucher) => {
  return voucher.can_edit || voucher.status === 'DRAFT';
};

/**
 * Check if voucher can be submitted
 */
export const canSubmitVoucher = (voucher) => {
  return voucher.can_submit || voucher.status === 'DRAFT';
};

/**
 * Check if voucher can be approved
 */
export const canApproveVoucher = (voucher) => {
  return voucher.can_approve || voucher.status === 'SUBMITTED';
};

/**
 * Check if voucher can be allocated
 */
export const canAllocateVoucher = (voucher) => {
  return voucher.can_allocate || voucher.status === 'APPROVED';
};

/**
 * Check if voucher can be posted to GL
 */
export const canPostToGL = (voucher) => {
  return voucher.status === 'ALLOCATED' && !voucher.posted_to_gl;
};

/**
 * Calculate unallocated amount
 */
export const calculateUnallocated = (voucher) => {
  const total = parseFloat(voucher.total_cost || 0);
  const allocated = parseFloat(voucher.allocated_cost || 0);
  return total - allocated;
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
 * Validate voucher data
 */
export const validateVoucherData = (data) => {
  const errors = {};

  if (!data.voucher_date) {
    errors.voucher_date = 'Voucher date is required';
  }

  if (!data.description || data.description.trim() === '') {
    errors.description = 'Description is required';
  }

  if (!data.total_cost || parseFloat(data.total_cost) <= 0) {
    errors.total_cost = 'Total cost must be greater than zero';
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
};

export default {
  fetchLandedCostVouchers,
  getLandedCostVoucher,
  createLandedCostVoucher,
  updateLandedCostVoucher,
  deleteLandedCostVoucher,
  submitVoucher,
  approveVoucher,
  cancelVoucher,
  generateAllocationPlan,
  allocateVoucher,
  postVoucherToGL,
  getVoucherSummary,
  fetchAllocations,
  reverseAllocation,
  VOUCHER_STATUS,
  VOUCHER_STATUS_LABELS,
  VOUCHER_STATUS_COLORS,
  APPORTIONMENT_METHODS,
  APPORTIONMENT_METHOD_LABELS,
  formatVoucherNumber,
  getStatusColor,
  getStatusLabel,
  canEditVoucher,
  canSubmitVoucher,
  canApproveVoucher,
  canAllocateVoucher,
  canPostToGL,
  calculateUnallocated,
  formatAmount,
  validateVoucherData,
};
