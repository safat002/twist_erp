import api from './api';

/**
 * Warehouse Validation Service
 *
 * Handles warehouse selection validation and override logging
 */

/**
 * Validate warehouse selection for a given item
 *
 * @param {number} budgetItemId - ID of the budget item
 * @param {number} selectedWarehouseId - ID of the selected warehouse
 * @returns {Promise<Object>} Validation result
 * {
 *   is_valid: boolean,
 *   warning_level: 'INFO' | 'WARNING' | 'CRITICAL',
 *   message: string,
 *   requires_reason: boolean,
 *   requires_approval: boolean,
 *   suggested_warehouse: { id, code, name },
 *   allowed_warehouses: [...]
 * }
 */
export const validateWarehouseSelection = async (budgetItemId, selectedWarehouseId) => {
  try {
    const response = await api.post('/api/v1/inventory/warehouse-mappings/validate_warehouse/', {
      budget_item_id: budgetItemId,
      selected_warehouse_id: selectedWarehouseId
    });
    return response.data;
  } catch (error) {
    console.error('Error validating warehouse selection:', error);
    throw error;
  }
};

/**
 * Get allowed warehouses for a given item
 *
 * @param {number} budgetItemId - ID of the budget item
 * @returns {Promise<Object>} Allowed warehouses and suggested warehouse
 * {
 *   allowed_warehouses: [...],
 *   suggested_warehouse: { id, code, name }
 * }
 */
export const getAllowedWarehouses = async (budgetItemId) => {
  try {
    const response = await api.get('/api/v1/inventory/warehouse-mappings/allowed_warehouses/', {
      params: { budget_item: budgetItemId }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching allowed warehouses:', error);
    throw error;
  }
};

/**
 * Log a warehouse override
 *
 * @param {Object} overrideData - Override log data
 * {
 *   transaction_type: string,  // e.g., 'GRN', 'MATERIAL_ISSUE'
 *   transaction_id: number,
 *   transaction_number: string,
 *   budget_item_id: number,
 *   suggested_warehouse_id: number,
 *   actual_warehouse_id: number,
 *   warning_level: 'INFO' | 'WARNING' | 'CRITICAL',
 *   override_reason: string,
 *   was_approved: boolean,
 *   approved_by_id: number (optional)
 * }
 * @returns {Promise<Object>} Log entry
 */
export const logWarehouseOverride = async (overrideData) => {
  try {
    const response = await api.post('/api/v1/inventory/warehouse-overrides/log_override/', overrideData);
    return response.data;
  } catch (error) {
    console.error('Error logging warehouse override:', error);
    throw error;
  }
};

/**
 * Get warehouse override logs
 *
 * @param {Object} filters - Query filters
 * @returns {Promise<Array>} List of override logs
 */
export const getWarehouseOverrideLogs = async (filters = {}) => {
  try {
    const response = await api.get('/api/v1/inventory/warehouse-overrides/', {
      params: filters
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching warehouse override logs:', error);
    throw error;
  }
};

/**
 * Get warehouse category mappings
 *
 * @param {Object} filters - Query filters
 * @returns {Promise<Array>} List of warehouse mappings
 */
export const getWarehouseMappings = async (filters = {}) => {
  try {
    const response = await api.get('/api/v1/inventory/warehouse-mappings/', {
      params: filters
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching warehouse mappings:', error);
    throw error;
  }
};

/**
 * Create a warehouse category mapping
 *
 * @param {Object} mappingData - Mapping configuration
 * @returns {Promise<Object>} Created mapping
 */
export const createWarehouseMapping = async (mappingData) => {
  try {
    const response = await api.post('/api/v1/inventory/warehouse-mappings/', mappingData);
    return response.data;
  } catch (error) {
    console.error('Error creating warehouse mapping:', error);
    throw error;
  }
};

/**
 * Update a warehouse category mapping
 *
 * @param {number} id - Mapping ID
 * @param {Object} mappingData - Updated mapping configuration
 * @returns {Promise<Object>} Updated mapping
 */
export const updateWarehouseMapping = async (id, mappingData) => {
  try {
    const response = await api.patch(`/api/v1/inventory/warehouse-mappings/${id}/`, mappingData);
    return response.data;
  } catch (error) {
    console.error('Error updating warehouse mapping:', error);
    throw error;
  }
};

/**
 * Delete a warehouse category mapping
 *
 * @param {number} id - Mapping ID
 * @returns {Promise<void>}
 */
export const deleteWarehouseMapping = async (id) => {
  try {
    await api.delete(`/api/v1/inventory/warehouse-mappings/${id}/`);
  } catch (error) {
    console.error('Error deleting warehouse mapping:', error);
    throw error;
  }
};

/**
 * Hook for warehouse validation in forms
 *
 * Usage in a form component:
 *
 * const warehouseValidation = useWarehouseValidation();
 *
 * // When warehouse is selected:
 * const handleWarehouseChange = async (warehouseId) => {
 *   const budgetItemId = form.getFieldValue('budget_item');
 *   if (budgetItemId) {
 *     const validation = await warehouseValidation.validate(budgetItemId, warehouseId);
 *     if (!validation.is_valid && validation.requires_reason) {
 *       // Show warning dialog
 *       setWarningDialogVisible(true);
 *       setValidationResult(validation);
 *     }
 *   }
 * };
 */
export const useWarehouseValidation = () => {
  const validate = async (budgetItemId, selectedWarehouseId) => {
    if (!budgetItemId || !selectedWarehouseId) {
      return {
        is_valid: true,
        warning_level: 'INFO',
        message: 'No validation required',
        requires_reason: false,
        requires_approval: false
      };
    }

    try {
      const result = await validateWarehouseSelection(budgetItemId, selectedWarehouseId);
      return result;
    } catch (error) {
      console.error('Validation error:', error);
      // Return default valid result if validation fails
      return {
        is_valid: true,
        warning_level: 'INFO',
        message: 'Validation check skipped due to error',
        requires_reason: false,
        requires_approval: false
      };
    }
  };

  const logOverride = async (overrideData) => {
    try {
      await logWarehouseOverride(overrideData);
    } catch (error) {
      console.error('Failed to log override:', error);
      // Don't block the transaction if logging fails
    }
  };

  return {
    validate,
    logOverride,
    getAllowedWarehouses,
    getOverrideLogs: getWarehouseOverrideLogs
  };
};

export default {
  validateWarehouseSelection,
  getAllowedWarehouses,
  logWarehouseOverride,
  getWarehouseOverrideLogs,
  getWarehouseMappings,
  createWarehouseMapping,
  updateWarehouseMapping,
  deleteWarehouseMapping,
  useWarehouseValidation
};
