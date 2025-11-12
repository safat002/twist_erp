/**
 * QC (Quality Control) & Compliance Service
 * Handles all QC inspection, stock hold, batch, and serial number operations
 */

import api from './api';

// ============================================================================
// STOCK HOLDS
// ============================================================================

export const getStockHolds = (params = {}) =>
  api.get('/api/v1/inventory/stock-holds/', { params });

export const getStockHold = (id) =>
  api.get(`/api/v1/inventory/stock-holds/${id}/`);

export const createStockHold = (data) =>
  api.post('/api/v1/inventory/stock-holds/', data);

export const updateStockHold = (id, data) =>
  api.patch(`/api/v1/inventory/stock-holds/${id}/`, data);

export const deleteStockHold = (id) =>
  api.delete(`/api/v1/inventory/stock-holds/${id}/`);

export const releaseStockHold = (id, data) =>
  api.post(`/api/v1/inventory/stock-holds/${id}/release/`, data);

// ============================================================================
// QC CHECKPOINTS
// ============================================================================

export const getQCCheckpoints = (params = {}) =>
  api.get('/api/v1/inventory/qc-checkpoints/', { params });

export const getQCCheckpoint = (id) =>
  api.get(`/api/v1/inventory/qc-checkpoints/${id}/`);

export const createQCCheckpoint = (data) =>
  api.post('/api/v1/inventory/qc-checkpoints/', data);

export const updateQCCheckpoint = (id, data) =>
  api.patch(`/api/v1/inventory/qc-checkpoints/${id}/`, data);

export const deleteQCCheckpoint = (id) =>
  api.delete(`/api/v1/inventory/qc-checkpoints/${id}/`);

// ============================================================================
// QC RESULTS
// ============================================================================

export const getQCResults = (params = {}) =>
  api.get('/api/v1/inventory/qc-results/', { params });

export const getQCResult = (id) =>
  api.get(`/api/v1/inventory/qc-results/${id}/`);

export const createQCResult = (data) =>
  api.post('/api/v1/inventory/qc-results/', data);

export const updateQCResult = (id, data) =>
  api.patch(`/api/v1/inventory/qc-results/${id}/`, data);

export const deleteQCResult = (id) =>
  api.delete(`/api/v1/inventory/qc-results/${id}/`);

export const getPendingInspections = (params = {}) =>
  api.get('/api/v1/inventory/qc-results/pending_inspections/', { params });

export const getQCStatistics = (params = {}) =>
  api.get('/api/v1/inventory/qc-results/statistics/', { params });

// ============================================================================
// BATCH LOTS
// ============================================================================

export const getBatchLots = (params = {}) =>
  api.get('/api/v1/inventory/batch-lots/', { params });

export const getBatchLot = (id) =>
  api.get(`/api/v1/inventory/batch-lots/${id}/`);

export const createBatchLot = (data) =>
  api.post('/api/v1/inventory/batch-lots/', data);

export const updateBatchLot = (id, data) =>
  api.patch(`/api/v1/inventory/batch-lots/${id}/`, data);

export const deleteBatchLot = (id) =>
  api.delete(`/api/v1/inventory/batch-lots/${id}/`);

export const disposeBatchLot = (id, data) =>
  api.post(`/api/v1/inventory/batch-lots/${id}/dispose/`, data);

// ============================================================================
// SERIAL NUMBERS
// ============================================================================

export const getSerialNumbers = (params = {}) =>
  api.get('/api/v1/inventory/serial-numbers/', { params });

export const getSerialNumber = (id) =>
  api.get(`/api/v1/inventory/serial-numbers/${id}/`);

export const createSerialNumber = (data) =>
  api.post('/api/v1/inventory/serial-numbers/', data);

export const updateSerialNumber = (id, data) =>
  api.patch(`/api/v1/inventory/serial-numbers/${id}/`, data);

export const deleteSerialNumber = (id) =>
  api.delete(`/api/v1/inventory/serial-numbers/${id}/`);

// ============================================================================
// CONSTANTS & ENUMS
// ============================================================================

export const HOLD_TYPES = {
  QC_INSPECTION: 'QC_INSPECTION',
  DOCUMENT_HOLD: 'DOCUMENT_HOLD',
  APPROVAL_PENDING: 'APPROVAL_PENDING',
  CUSTOMER_RETURN: 'CUSTOMER_RETURN',
  DEFECT: 'DEFECT',
  OTHER: 'OTHER',
};

export const HOLD_TYPE_LABELS = {
  QC_INSPECTION: 'QC Inspection',
  DOCUMENT_HOLD: 'Document Hold',
  APPROVAL_PENDING: 'Approval Pending',
  CUSTOMER_RETURN: 'Customer Return',
  DEFECT: 'Defect',
  OTHER: 'Other',
};

export const HOLD_STATUSES = {
  ACTIVE: 'ACTIVE',
  RELEASED: 'RELEASED',
  SCRAPPED: 'SCRAPPED',
  RETURNED: 'RETURNED',
};

export const HOLD_STATUS_LABELS = {
  ACTIVE: 'Active',
  RELEASED: 'Released',
  SCRAPPED: 'Scrapped',
  RETURNED: 'Returned',
};

export const HOLD_STATUS_COLORS = {
  ACTIVE: 'orange',
  RELEASED: 'green',
  SCRAPPED: 'red',
  RETURNED: 'blue',
};

export const DISPOSITIONS = {
  TO_WAREHOUSE: 'TO_WAREHOUSE',
  SCRAP: 'SCRAP',
  RETURN: 'RETURN',
  REWORK: 'REWORK',
  REJECT: 'REJECT',
};

export const DISPOSITION_LABELS = {
  TO_WAREHOUSE: 'Move to Warehouse',
  SCRAP: 'Scrap',
  RETURN: 'Return to Supplier',
  REWORK: 'Rework',
  REJECT: 'Reject',
};

export const QC_STATUSES = {
  PASS: 'PASS',
  FAIL: 'FAIL',
  CONDITIONAL_PASS: 'CONDITIONAL_PASS',
};

export const QC_STATUS_LABELS = {
  PASS: 'Pass',
  FAIL: 'Fail',
  CONDITIONAL_PASS: 'Conditional Pass',
};

export const QC_STATUS_COLORS = {
  PASS: 'green',
  FAIL: 'red',
  CONDITIONAL_PASS: 'orange',
};

export const REJECTION_REASONS = {
  DAMAGE: 'DAMAGE',
  INCOMPLETE_DOC: 'INCOMPLETE_DOC',
  WRONG_ITEM: 'WRONG_ITEM',
  QUANTITY_DISCREPANCY: 'QUANTITY_DISCREPANCY',
  QUALITY_ISSUE: 'QUALITY_ISSUE',
  EXPIRY_ISSUE: 'EXPIRY_ISSUE',
  OTHER: 'OTHER',
};

export const REJECTION_REASON_LABELS = {
  DAMAGE: 'Damage',
  INCOMPLETE_DOC: 'Incomplete Documentation',
  WRONG_ITEM: 'Wrong Item',
  QUANTITY_DISCREPANCY: 'Quantity Discrepancy',
  QUALITY_ISSUE: 'Quality Issue',
  EXPIRY_ISSUE: 'Expiry/Date Issue',
  OTHER: 'Other',
};

export const BATCH_STATUSES = {
  QUARANTINE: 'QUARANTINE',
  ON_HOLD: 'ON_HOLD',
  RELEASED: 'RELEASED',
  SCRAP: 'SCRAP',
};

export const BATCH_STATUS_LABELS = {
  QUARANTINE: 'Quarantine',
  ON_HOLD: 'On Hold',
  RELEASED: 'Released',
  SCRAP: 'Scrap',
};

export const BATCH_STATUS_COLORS = {
  QUARANTINE: 'orange',
  ON_HOLD: 'red',
  RELEASED: 'green',
  SCRAP: 'gray',
};

export const SERIAL_STATUSES = {
  IN_STOCK: 'IN_STOCK',
  ASSIGNED: 'ASSIGNED',
  ISSUED: 'ISSUED',
  RETURNED: 'RETURNED',
  SCRAPPED: 'SCRAPPED',
};

export const SERIAL_STATUS_LABELS = {
  IN_STOCK: 'In Stock',
  ASSIGNED: 'Assigned to Order',
  ISSUED: 'Issued',
  RETURNED: 'Returned',
  SCRAPPED: 'Scrapped',
};

export const SERIAL_STATUS_COLORS = {
  IN_STOCK: 'green',
  ASSIGNED: 'blue',
  ISSUED: 'orange',
  RETURNED: 'purple',
  SCRAPPED: 'red',
};

export const DISPOSAL_METHODS = {
  SCRAP: 'SCRAP',
  DONATE: 'DONATE',
  RETURN_TO_SUPPLIER: 'RETURN_TO_SUPPLIER',
  REWORK: 'REWORK',
};

export const DISPOSAL_METHOD_LABELS = {
  SCRAP: 'Scrap',
  DONATE: 'Donate',
  RETURN_TO_SUPPLIER: 'Return to Supplier',
  REWORK: 'Rework',
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export const getExpiryColor = (daysUntilExpiry) => {
  if (daysUntilExpiry === null) return 'default';
  if (daysUntilExpiry < 0) return 'red';
  if (daysUntilExpiry <= 7) return 'red';
  if (daysUntilExpiry <= 30) return 'orange';
  return 'green';
};

export const getExpiryStatus = (daysUntilExpiry) => {
  if (daysUntilExpiry === null) return null;
  if (daysUntilExpiry < 0) return 'Expired';
  if (daysUntilExpiry === 0) return 'Expires Today';
  if (daysUntilExpiry === 1) return 'Expires Tomorrow';
  if (daysUntilExpiry <= 7) return `Expires in ${daysUntilExpiry} days`;
  if (daysUntilExpiry <= 30) return `Expires in ${daysUntilExpiry} days`;
  return `${daysUntilExpiry} days`;
};

export const formatRejectionPercentage = (qtyInspected, qtyRejected) => {
  if (!qtyInspected || qtyInspected === 0) return '0%';
  const percentage = (qtyRejected / qtyInspected) * 100;
  return `${percentage.toFixed(1)}%`;
};

export const shouldEscalate = (qtyInspected, qtyRejected, threshold) => {
  if (!qtyInspected || qtyInspected === 0) return false;
  const percentage = (qtyRejected / qtyInspected) * 100;
  return percentage > threshold;
};

export default {
  // Stock Holds
  getStockHolds,
  getStockHold,
  createStockHold,
  updateStockHold,
  deleteStockHold,
  releaseStockHold,

  // QC Checkpoints
  getQCCheckpoints,
  getQCCheckpoint,
  createQCCheckpoint,
  updateQCCheckpoint,
  deleteQCCheckpoint,

  // QC Results
  getQCResults,
  getQCResult,
  createQCResult,
  updateQCResult,
  deleteQCResult,
  getPendingInspections,
  getQCStatistics,

  // Batch Lots
  getBatchLots,
  getBatchLot,
  createBatchLot,
  updateBatchLot,
  deleteBatchLot,
  disposeBatchLot,

  // Serial Numbers
  getSerialNumbers,
  getSerialNumber,
  createSerialNumber,
  updateSerialNumber,
  deleteSerialNumber,

  // Constants
  HOLD_TYPES,
  HOLD_TYPE_LABELS,
  HOLD_STATUSES,
  HOLD_STATUS_LABELS,
  HOLD_STATUS_COLORS,
  DISPOSITIONS,
  DISPOSITION_LABELS,
  QC_STATUSES,
  QC_STATUS_LABELS,
  QC_STATUS_COLORS,
  REJECTION_REASONS,
  REJECTION_REASON_LABELS,
  BATCH_STATUSES,
  BATCH_STATUS_LABELS,
  BATCH_STATUS_COLORS,
  SERIAL_STATUSES,
  SERIAL_STATUS_LABELS,
  SERIAL_STATUS_COLORS,
  DISPOSAL_METHODS,
  DISPOSAL_METHOD_LABELS,

  // Helpers
  getExpiryColor,
  getExpiryStatus,
  formatRejectionPercentage,
  shouldEscalate,
};
