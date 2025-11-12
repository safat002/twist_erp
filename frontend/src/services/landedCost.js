import api from './api';

/**
 * Enhanced Landed Cost API Service
 * Handles multi-component landed costs with per-line apportionment
 */

const landedCostService = {
  // ========================================
  // LANDED COST COMPONENTS
  // ========================================

  /**
   * Get list of landed cost components
   */
  getLandedCostComponents: async (params = {}) => {
    const response = await api.get('/inventory/landed-costs/', { params });
    return response.data;
  },

  /**
   * Get specific landed cost component by ID
   */
  getLandedCostComponent: async (id) => {
    const response = await api.get(`/inventory/landed-costs/${id}/`);
    return response.data;
  },

  /**
   * Get component summary with line details
   */
  getComponentSummary: async (id) => {
    const response = await api.get(`/inventory/landed-costs/${id}/summary/`);
    return response.data;
  },

  /**
   * Get landed cost summary for a GRN
   */
  getGRNLandedCostSummary: async (grnId) => {
    const response = await api.get(`/inventory/landed-costs/grn/${grnId}/summary/`);
    return response.data;
  },

  // ========================================
  // PREVIEW & APPLY
  // ========================================

  /**
   * Preview landed cost apportionment before applying
   *
   * @param {number} grnId - Goods Receipt ID
   * @param {Array} components - Array of {component_type, total_amount, description, etc.}
   * @param {string} apportionmentMethod - 'QUANTITY', 'VALUE', 'WEIGHT', 'VOLUME', or 'MANUAL'
   */
  previewApportionment: async (grnId, components, apportionmentMethod = 'QUANTITY') => {
    const response = await api.post('/inventory/landed-costs/preview/', {
      goods_receipt: grnId,
      components,
      apportionment_method: apportionmentMethod
    });
    return response.data;
  },

  /**
   * Apply landed costs to a GRN
   *
   * @param {number} grnId - Goods Receipt ID
   * @param {Array} components - Array of component objects
   * @param {string} apportionmentMethod - Apportionment method
   * @param {string} notes - Optional notes
   */
  applyLandedCosts: async (grnId, components, apportionmentMethod = 'QUANTITY', notes = '') => {
    const response = await api.post('/inventory/landed-costs/apply/', {
      goods_receipt: grnId,
      components,
      apportionment_method: apportionmentMethod,
      notes
    });
    return response.data;
  },

  /**
   * Reverse a landed cost component
   *
   * @param {number} componentId - Component ID to reverse
   * @param {string} reason - Reason for reversal
   */
  reverseLandedCost: async (componentId, reason) => {
    const response = await api.post(`/inventory/landed-costs/${componentId}/reverse/`, {
      reason
    });
    return response.data;
  },

  // ========================================
  // HELPER FUNCTIONS & CONSTANTS
  // ========================================

  /**
   * Component types available
   */
  COMPONENT_TYPES: {
    FREIGHT: 'Freight / Shipping',
    INSURANCE: 'Insurance',
    CUSTOMS_DUTY: 'Customs Duty',
    IMPORT_TAX: 'Import Tax',
    BROKERAGE: 'Brokerage Fees',
    PORT_HANDLING: 'Port Handling',
    DEMURRAGE: 'Demurrage',
    INSPECTION: 'Inspection Fees',
    OTHER: 'Other Charges'
  },

  /**
   * Apportionment methods
   */
  APPORTIONMENT_METHODS: {
    QUANTITY: 'By Quantity',
    VALUE: 'By Line Value',
    WEIGHT: 'By Weight',
    VOLUME: 'By Volume',
    MANUAL: 'Manual Allocation'
  },

  /**
   * Get component type options for dropdown
   */
  getComponentTypeOptions: () => {
    return Object.entries(landedCostService.COMPONENT_TYPES).map(([value, label]) => ({
      value,
      label
    }));
  },

  /**
   * Get apportionment method options for dropdown
   */
  getApportionmentMethodOptions: () => {
    return Object.entries(landedCostService.APPORTIONMENT_METHODS).map(([value, label]) => ({
      value,
      label
    }));
  },

  /**
   * Format landed cost amount
   */
  formatAmount: (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2
    }).format(amount);
  },

  /**
   * Calculate total landed cost from components
   */
  calculateTotalLandedCost: (components) => {
    return components.reduce((sum, c) => sum + parseFloat(c.total_amount || 0), 0);
  },

  /**
   * Validate component data before submission
   */
  validateComponents: (components) => {
    const errors = [];

    if (!components || components.length === 0) {
      errors.push('At least one cost component is required');
      return errors;
    }

    components.forEach((component, index) => {
      if (!component.component_type) {
        errors.push(`Component ${index + 1}: Type is required`);
      }
      if (!component.total_amount || parseFloat(component.total_amount) <= 0) {
        errors.push(`Component ${index + 1}: Amount must be greater than zero`);
      }
    });

    return errors;
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
   * Calculate apportionment percentage
   */
  calculatePercentage: (lineValue, totalValue) => {
    if (totalValue === 0) return 0;
    return (lineValue / totalValue * 100).toFixed(2);
  },

  /**
   * Generate preview summary statistics
   */
  generatePreviewSummary: (previewData) => {
    const totalLines = previewData.lines?.length || 0;
    const totalComponents = previewData.lines?.[0]?.component_apportionments?.length || 0;

    const totalToInventory = previewData.lines?.reduce((sum, line) =>
      sum + line.component_apportionments.reduce((cSum, c) => cSum + (c.to_inventory || 0), 0), 0
    ) || 0;

    const totalToCOGS = previewData.lines?.reduce((sum, line) =>
      sum + line.component_apportionments.reduce((cSum, c) => cSum + (c.to_cogs || 0), 0), 0
    ) || 0;

    return {
      total_lines: totalLines,
      total_components: totalComponents,
      total_to_inventory: totalToInventory,
      total_to_cogs: totalToCOGS,
      total_landed_cost: previewData.total_landed_cost || 0,
      method: previewData.apportionment_method
    };
  },

  /**
   * Export preview to CSV
   */
  exportPreviewToCSV: (previewData) => {
    const headers = [
      'Product Code',
      'Product Name',
      'Quantity',
      'Original Unit Cost',
      'Component Type',
      'Apportioned Amount',
      'To Inventory',
      'To COGS',
      'Cost Adjustment',
      'New Unit Cost'
    ];

    const rows = [];

    previewData.lines?.forEach(line => {
      line.component_apportionments?.forEach(comp => {
        rows.push([
          line.product_code,
          line.product_name,
          line.quantity,
          line.original_unit_cost,
          comp.component_type_display,
          comp.apportioned_amount,
          comp.to_inventory,
          comp.to_cogs,
          comp.cost_per_unit_adjustment,
          line.new_unit_cost
        ]);
      });
    });

    return {
      headers,
      rows,
      filename: `landed_cost_preview_grn_${previewData.grn_id}.csv`
    };
  }
};

export default landedCostService;
