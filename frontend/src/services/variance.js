import api from './api';

/**
 * Variance Tracking API Service
 * Handles standard cost variance and purchase price variance operations
 */

const varianceService = {
  // ========================================
  // STANDARD COST VARIANCE
  // ========================================

  /**
   * Get list of standard cost variances
   */
  getStandardCostVariances: async (params = {}) => {
    const response = await api.get('/inventory/variances/standard-cost/', { params });
    return response.data;
  },

  /**
   * Get specific standard cost variance by ID
   */
  getStandardCostVariance: async (id) => {
    const response = await api.get(`/inventory/variances/standard-cost/${id}/`);
    return response.data;
  },

  /**
   * Create standard cost variance record
   */
  createStandardCostVariance: async (data) => {
    const response = await api.post('/inventory/variances/standard-cost/', data);
    return response.data;
  },

  /**
   * Post standard cost variance to GL
   */
  postStandardVarianceToGL: async (id) => {
    const response = await api.post(`/inventory/variances/standard-cost/${id}/post_to_gl/`);
    return response.data;
  },

  // ========================================
  // PURCHASE PRICE VARIANCE
  // ========================================

  /**
   * Get list of purchase price variances
   */
  getPurchasePriceVariances: async (params = {}) => {
    const response = await api.get('/inventory/variances/purchase-price/', { params });
    return response.data;
  },

  /**
   * Get specific purchase price variance by ID
   */
  getPurchasePriceVariance: async (id) => {
    const response = await api.get(`/inventory/variances/purchase-price/${id}/`);
    return response.data;
  },

  /**
   * Create purchase price variance record
   */
  createPurchasePriceVariance: async (data) => {
    const response = await api.post('/inventory/variances/purchase-price/', data);
    return response.data;
  },

  /**
   * Post purchase price variance to GL
   */
  postPPVToGL: async (id) => {
    const response = await api.post(`/inventory/variances/purchase-price/${id}/post_to_gl/`);
    return response.data;
  },

  // ========================================
  // VARIANCE SUMMARY & REPORTING
  // ========================================

  /**
   * Get variance summary for reporting
   */
  getVarianceSummary: async (params = {}) => {
    const response = await api.get('/inventory/variances/summary/', { params });
    return response.data;
  },

  // ========================================
  // HELPER FUNCTIONS
  // ========================================

  /**
   * Format variance amount with color coding
   */
  formatVariance: (amount, type) => {
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(Math.abs(amount));

    return {
      amount: formatted,
      color: type === 'FAVORABLE' ? 'green' : 'red',
      icon: type === 'FAVORABLE' ? '↓' : '↑',
      label: type === 'FAVORABLE' ? 'Favorable' : 'Unfavorable'
    };
  },

  /**
   * Calculate variance percentage
   */
  calculateVariancePercentage: (actual, standard) => {
    if (standard === 0) return 0;
    return ((actual - standard) / standard * 100).toFixed(2);
  },

  /**
   * Get variance type badge color
   */
  getVarianceColor: (type) => {
    return type === 'FAVORABLE' ? 'success' : 'error';
  },

  /**
   * Get posting status badge
   */
  getPostingStatusBadge: (posted, jeId = null) => {
    if (posted) {
      return {
        label: jeId ? `Posted (JE#${jeId})` : 'Posted',
        color: 'success',
        icon: 'check'
      };
    }
    return {
      label: 'Pending',
      color: 'warning',
      icon: 'clock'
    };
  },

  /**
   * Aggregate variance statistics
   */
  aggregateVarianceStats: (variances) => {
    const favorable = variances
      .filter(v => v.variance_type === 'FAVORABLE')
      .reduce((sum, v) => sum + Math.abs(v.total_variance_amount), 0);

    const unfavorable = variances
      .filter(v => v.variance_type === 'UNFAVORABLE')
      .reduce((sum, v) => sum + v.total_variance_amount, 0);

    return {
      total_favorable: favorable,
      total_unfavorable: unfavorable,
      net_variance: unfavorable - favorable,
      count: variances.length,
      posted_count: variances.filter(v => v.posted_to_gl).length,
      pending_count: variances.filter(v => !v.posted_to_gl).length
    };
  }
};

export default varianceService;
