/**
 * Inventory Valuation Service
 * API client for managing inventory valuation methods, cost layers, and reports
 */

import api from './api';

const valuationService = {
  // ==========================================
  // VALUATION METHODS
  // ==========================================

  /**
   * Get all valuation methods with optional filters
   * @param {Object} filters - Optional filters (product, warehouse, method, active_only)
   * @returns {Promise<Array>} List of valuation methods
   */
  async getValuationMethods(filters = {}) {
    const params = new URLSearchParams();
    if (filters.product) params.append('product', filters.product);
    if (filters.warehouse) params.append('warehouse', filters.warehouse);
    if (filters.method) params.append('method', filters.method);
    if (filters.active_only) params.append('active_only', 'true');

    const response = await api.get(`/inventory/valuation-methods/?${params.toString()}`);
    return response.data;
  },

  /**
   * Get a specific valuation method by ID
   * @param {number} id - Valuation method ID
   * @returns {Promise<Object>} Valuation method details
   */
  async getValuationMethod(id) {
    const response = await api.get(`/inventory/valuation-methods/${id}/`);
    return response.data;
  },

  /**
   * Get valuation method for specific product/warehouse combination
   * @param {number} productId - Product ID
   * @param {number} warehouseId - Warehouse ID
   * @returns {Promise<Object>} Valuation method or null
   */
  async getValuationMethodByProductWarehouse(productId, warehouseId) {
    try {
      const response = await api.get('/inventory/valuation-methods/by_product_warehouse/', {
        params: { product_id: productId, warehouse_id: warehouseId }
      });
      return response.data;
    } catch (error) {
      if (error.response && error.response.status === 404) {
        return null; // No method configured, will use default FIFO
      }
      throw error;
    }
  },

  /**
   * Create a new valuation method
   * @param {Object} data - Valuation method data
   * @returns {Promise<Object>} Created valuation method
   */
  async createValuationMethod(data) {
    const response = await api.post('/inventory/valuation-methods/', data);
    return response.data;
  },

  /**
   * Update a valuation method
   * @param {number} id - Valuation method ID
   * @param {Object} data - Updated data
   * @returns {Promise<Object>} Updated valuation method
   */
  async updateValuationMethod(id, data) {
    const response = await api.put(`/inventory/valuation-methods/${id}/`, data);
    return response.data;
  },

  /**
   * Partially update a valuation method
   * @param {number} id - Valuation method ID
   * @param {Object} data - Partial data to update
   * @returns {Promise<Object>} Updated valuation method
   */
  async patchValuationMethod(id, data) {
    const response = await api.patch(`/inventory/valuation-methods/${id}/`, data);
    return response.data;
  },

  /**
   * Delete a valuation method
   * @param {number} id - Valuation method ID
   * @returns {Promise<void>}
   */
  async deleteValuationMethod(id) {
    await api.delete(`/inventory/valuation-methods/${id}/`);
  },

  // ==========================================
  // COST LAYERS
  // ==========================================

  /**
   * Get all cost layers with optional filters
   * @param {Object} filters - Optional filters (product, warehouse, open_only, batch_no)
   * @returns {Promise<Array>} List of cost layers
   */
  async getCostLayers(filters = {}) {
    const params = new URLSearchParams();
    if (filters.product) params.append('product', filters.product);
    if (filters.warehouse) params.append('warehouse', filters.warehouse);
    if (filters.open_only) params.append('open_only', 'true');
    if (filters.batch_no) params.append('batch_no', filters.batch_no);

    const response = await api.get(`/inventory/cost-layers/?${params.toString()}`);
    return response.data;
  },

  /**
   * Get a specific cost layer by ID (detailed view)
   * @param {number} id - Cost layer ID
   * @returns {Promise<Object>} Cost layer details
   */
  async getCostLayer(id) {
    const response = await api.get(`/inventory/cost-layers/${id}/`);
    return response.data;
  },

  /**
   * Get cost layer summary for a product/warehouse
   * @param {number} productId - Product ID
   * @param {number} warehouseId - Warehouse ID
   * @returns {Promise<Object>} Summary with inventory value and open layers
   */
  async getCostLayerSummary(productId, warehouseId) {
    const response = await api.get('/inventory/cost-layers/summary/', {
      params: { product_id: productId, warehouse_id: warehouseId }
    });
    return response.data;
  },

  // ==========================================
  // VALUATION CHANGE LOGS
  // ==========================================

  /**
   * Get all valuation change logs with optional filters
   * @param {Object} filters - Optional filters (status, product)
   * @returns {Promise<Array>} List of change logs
   */
  async getValuationChanges(filters = {}) {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.product) params.append('product', filters.product);

    const response = await api.get(`/inventory/valuation-changes/?${params.toString()}`);
    return response.data;
  },

  /**
   * Get a specific valuation change log by ID
   * @param {number} id - Change log ID
   * @returns {Promise<Object>} Change log details
   */
  async getValuationChange(id) {
    const response = await api.get(`/inventory/valuation-changes/${id}/`);
    return response.data;
  },

  /**
   * Create a new valuation change request
   * @param {Object} data - Change request data
   * @returns {Promise<Object>} Created change log
   */
  async createValuationChange(data) {
    const response = await api.post('/inventory/valuation-changes/', data);
    return response.data;
  },

  /**
   * Approve a valuation change request
   * @param {number} id - Change log ID
   * @returns {Promise<Object>} Updated change log
   */
  async approveValuationChange(id) {
    const response = await api.post(`/inventory/valuation-changes/${id}/approve/`);
    return response.data;
  },

  /**
   * Reject a valuation change request
   * @param {number} id - Change log ID
   * @param {string} rejectionReason - Reason for rejection
   * @returns {Promise<Object>} Updated change log
   */
  async rejectValuationChange(id, rejectionReason) {
    const response = await api.post(`/inventory/valuation-changes/${id}/reject/`, {
      rejection_reason: rejectionReason
    });
    return response.data;
  },

  // ==========================================
  // REPORTS & QUERIES
  // ==========================================

  /**
   * Generate inventory valuation report
   * @param {Object} filters - Optional filters (product_id, warehouse_id, method)
   * @returns {Promise<Object>} Valuation report with items and totals
   */
  async getValuationReport(filters = {}) {
    const params = new URLSearchParams();
    if (filters.product_id) params.append('product_id', filters.product_id);
    if (filters.warehouse_id) params.append('warehouse_id', filters.warehouse_id);
    if (filters.method) params.append('method', filters.method);

    const response = await api.get(`/inventory/valuation/report/?${params.toString()}`);
    return response.data;
  },

  /**
   * Get current cost for a product/warehouse
   * @param {number} productId - Product ID
   * @param {number} warehouseId - Warehouse ID
   * @returns {Promise<Object>} Current cost information
   */
  async getCurrentCost(productId, warehouseId) {
    const response = await api.get('/inventory/valuation/current-cost/', {
      params: { product_id: productId, warehouse_id: warehouseId }
    });
    return response.data;
  },

  /**
   * Apply landed cost adjustment to a Goods Receipt
   * @param {number} goodsReceiptId - GRN ID
   * @param {number} totalAdjustment - Total landed cost amount
   * @param {'QUANTITY'|'VALUE'} method - Apportionment method
   * @param {string} reason - Reason text
   * @returns {Promise<Object>} Result summary
   */
  async applyLandedCostAdjustment(goodsReceiptId, totalAdjustment, method = 'QUANTITY', reason = '') {
    const payload = { goods_receipt_id: goodsReceiptId, total_adjustment: totalAdjustment, method, reason };
    const response = await api.post('/inventory/valuation/landed-cost-adjustment/', payload);
    return response.data;
  },

  /**
   * Fetch Goods Receipts (optionally filtered)
   * @param {Object} filters - Optional filters (status, supplier, date)
   * @returns {Promise<Array>} List of GRNs
   */
  async getGoodsReceipts(filters = {}) {
    const response = await api.get('/inventory/goods-receipts/', { params: filters });
    return response.data?.results || response.data || [];
  },

  // ==========================================
  // HELPER METHODS
  // ==========================================

  /**
   * Get valuation method choices (for dropdowns)
   * @returns {Array<Object>} Array of {value, label} objects
   */
  getValuationMethodChoices() {
    return [
      { value: 'FIFO', label: 'First In, First Out (FIFO)' },
      { value: 'LIFO', label: 'Last In, First Out (LIFO)' },
      { value: 'WEIGHTED_AVG', label: 'Weighted Average' },
      { value: 'STANDARD', label: 'Standard Cost' }
    ];
  },

  /**
   * Get average period choices (for weighted average)
   * @returns {Array<Object>} Array of {value, label} objects
   */
  getAveragePeriodChoices() {
    return [
      { value: 'PERPETUAL', label: 'Perpetual (Moving Average)' },
      { value: 'DAILY', label: 'Daily' },
      { value: 'WEEKLY', label: 'Weekly' },
      { value: 'MONTHLY', label: 'Monthly' }
    ];
  },

  /**
   * Get status choices for valuation changes
   * @returns {Array<Object>} Array of {value, label} objects
   */
  getStatusChoices() {
    return [
      { value: 'PENDING', label: 'Pending Approval' },
      { value: 'APPROVED', label: 'Approved' },
      { value: 'REJECTED', label: 'Rejected' },
      { value: 'EFFECTIVE', label: 'Effective (Applied)' }
    ];
  },

  /**
   * Get color for valuation method (for UI badges)
   * @param {string} method - Valuation method code
   * @returns {string} Color code
   */
  getMethodColor(method) {
    const colors = {
      'FIFO': '#17a2b8',
      'LIFO': '#6c757d',
      'WEIGHTED_AVG': '#28a745',
      'STANDARD': '#ffc107'
    };
    return colors[method] || '#6c757d';
  },

  /**
   * Get color for change status (for UI badges)
   * @param {string} status - Status code
   * @returns {string} Color code
   */
  getStatusColor(status) {
    const colors = {
      'PENDING': '#ffc107',
      'APPROVED': '#28a745',
      'REJECTED': '#dc3545',
      'EFFECTIVE': '#17a2b8'
    };
    return colors[status] || '#6c757d';
  },

  /**
   * Format currency value
   * @param {number} value - Numeric value
   * @param {string} currency - Currency symbol (default: ৳)
   * @returns {string} Formatted currency string
   */
  formatCurrency(value, currency = '৳') {
    return `${currency} ${Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  },

  /**
   * Format percentage
   * @param {number} value - Numeric value (0-100)
   * @returns {string} Formatted percentage string
   */
  formatPercentage(value) {
    return `${Number(value).toFixed(2)}%`;
  },

  /**
   * Calculate percentage consumed from layer
   * @param {Object} layer - Cost layer object
   * @returns {number} Percentage consumed (0-100)
   */
  calculateConsumedPercentage(layer) {
    if (layer.qty_received > 0) {
      const consumed = layer.qty_received - layer.qty_remaining;
      return (consumed / layer.qty_received) * 100;
    }
    return 0;
  }
};

export default valuationService;
