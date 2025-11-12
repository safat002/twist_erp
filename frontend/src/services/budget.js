import api from './api';

export const fetchBudgetWorkspaceSummary = () => api.get('/api/v1/budgets/workspace/summary/');

export const fetchCostCenters = (params = {}) =>
  api.get('/api/v1/budgets/cost-centers/', { params });

export const createCostCenter = (payload) => api.post('/api/v1/budgets/cost-centers/', payload);

export const updateCostCenter = (id, payload) =>
  api.patch(`/api/v1/budgets/cost-centers/${id}/`, payload);

export const fetchBudgets = (params = {}) => api.get('/api/v1/budgets/periods/', { params });
// Fetch a single budget by id (detail)
export const fetchBudget = (id) => api.get(`/api/v1/budgets/periods/${id}/`);

export const createBudget = (payload) => api.post('/api/v1/budgets/periods/', payload);

export const updateBudget = (id, payload) =>
  api.patch(`/api/v1/budgets/periods/${id}/`, payload);

export const submitBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/submit/`);

export const approveBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/approve/`);

export const lockBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/lock/`);

export const closeBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/close/`);

export const recalculateBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/recalculate/`);

export const fetchBudgetLines = (params = {}) => api.get('/api/v1/budgets/lines/', { params });
export const fetchBudgetAllLines = (budgetId) => api.get(`/api/v1/budgets/periods/${budgetId}/all_lines/`);

export const createBudgetLine = (payload) => api.post('/api/v1/budgets/lines/', payload);

export const updateBudgetLine = (id, payload) =>
  api.patch(`/api/v1/budgets/lines/${id}/`, payload);

// Review period actions on a single line (used by CC owners too)
export const sendBackLineForReview = (id, reason = '') =>
  api.post(`/api/v1/budgets/lines/${id}/send_back_for_review/`, { reason });

export const deleteBudgetLine = (id) => api.delete(`/api/v1/budgets/lines/${id}/`);

export const recordBudgetUsage = (payload) => api.post('/api/v1/budgets/usage/', payload);

export const fetchOverrides = (params = {}) => api.get('/api/v1/budgets/overrides/', { params });

export const createOverrideRequest = (payload) => api.post('/api/v1/budgets/overrides/', payload);

export const approveOverride = (id, notes) =>
  api.post(`/api/v1/budgets/overrides/${id}/approve/`, notes ? { notes } : {});

export const rejectOverride = (id, notes) =>
  api.post(`/api/v1/budgets/overrides/${id}/reject/`, notes ? { notes } : {});

export const checkBudgetAvailability = (payload) =>
  api.post('/api/v1/budgets/check-availability/', payload);

export const fetchBudgetSnapshots = (params = {}) =>
  api.get('/api/v1/budgets/snapshots/', { params });

export const createBudgetSnapshot = (payload) => api.post('/api/v1/budgets/snapshots/', payload);

// New workflow endpoints (aligned with docs/budget_module_plan.md)
export const openEntry = (id, payload = {}) => api.post(`/api/v1/budgets/periods/${id}/open_entry/`, payload);
export const closeEntry = (id) => api.post(`/api/v1/budgets/periods/${id}/close_entry/`);
export const submitForApproval = (id) => api.post(`/api/v1/budgets/periods/${id}/submit_for_approval/`);
export const approveBudgetName = (budgetId, payload) =>
  api.post(`/api/v1/budgets/periods/${budgetId}/approve_name/`, payload);
export const rejectBudgetName = (budgetId, payload) =>
  api.post(`/api/v1/budgets/periods/${budgetId}/reject_name/`, payload);

export const approveCC = (budgetId, payload) =>
  api.post(`/api/v1/budgets/periods/${budgetId}/approve_cc/`, payload);
export const rejectCC = (id, payload = {}) => api.post(`/api/v1/budgets/periods/${id}/reject_cc/`, payload);
export const requestFinalApproval = (id) => api.post(`/api/v1/budgets/periods/${id}/request_final_approval/`);
export const approveFinal = (id, payload = {}) => api.post(`/api/v1/budgets/periods/${id}/approve_final/`, payload);
export const rejectFinal = (id, payload = {}) => api.post(`/api/v1/budgets/periods/${id}/reject_final/`, payload);
export const fetchApprovalQueue = () => api.get('/api/v1/budgets/approvals/queue/');
// Approval detail and item-level approvals for final approvers
export const fetchApproval = (id) => api.get(`/api/v1/budgets/approvals/${id}/`);
export const approveApprovalLines = (id, { line_ids }) => api.post(`/api/v1/budgets/approvals/${id}/approve_lines/`, { line_ids });
export const fetchApprovalTaskDetails = (id) => api.get(`/api/v1/budgets/approvals/${id}/`);
export const approveBudgetLines = (id, line_ids) => api.post(`/api/v1/budgets/approvals/${id}/approve_lines/`, { line_ids });
export const activateBudget = (id) => api.post(`/api/v1/budgets/periods/${id}/activate/`);

// Name approval helper (for registry Drafts shown via fallback)
export const requestNameApproval = (id) => api.post(`/api/v1/budgets/periods/${id}/request_name_approval/`);

// Entry APIs (company-wide declared budgets → CC budgets)
export const fetchDeclaredBudgetsEntry = (params = {}) => api.get('/api/v1/budgets/entry/declared/', { params });
export const fetchPermittedCostCentersEntry = () => api.get('/api/v1/budgets/entry/cost-centers/');
export const fetchEntrySummary = (declaredId) => api.get('/api/v1/budgets/entry/summary/', { params: { budget: declaredId } });
export const fetchEntryLines = (declaredId, costCenterId) => api.get('/api/v1/budgets/entry/lines/', { params: { budget: declaredId, cost_center: costCenterId } });
export const getEntryPrice = (itemCode) => api.get('/api/v1/budgets/entry/price/', { params: { item_code: itemCode } });
export const addBudgetItem = (payload) => api.post('/api/v1/budgets/entry/add/', payload);
export const submitEntry = (payload) => api.post('/api/v1/budgets/entry/submit/', payload);

// Review period controls
export const startReviewPeriod = (id) => api.post(`/api/v1/budgets/periods/${id}/start_review_period/`);
export const closeReviewPeriod = (id) => api.post(`/api/v1/budgets/periods/${id}/close_review_period/`);
export const getReviewPeriodStatus = (id) => api.get(`/api/v1/budgets/periods/${id}/review_period_status/`);

// Moderator endpoints
export const fetchModeratorQueue = () => api.get('/api/v1/budgets/periods/moderator_queue/');
export const fetchModeratorReviewSummary = (id) => api.get(`/api/v1/budgets/periods/${id}/moderator_review_summary/`);
export const completeModeratorReview = (id, { summary_notes } = {}) =>
  api.post(`/api/v1/budgets/periods/${id}/complete_moderator_review/`, summary_notes ? { summary_notes } : {});

// Moderator actions on lines
export const addModeratorRemark = (lineId, { remark_text, remark_template_id } = {}) =>
  api.post(`/api/v1/budgets/lines/${lineId}/add_moderator_remark/`, { remark_text, remark_template_id });

export const batchAddRemarks = ({ budget_line_ids, remark_text, remark_template_id }) =>
  api.post('/api/v1/budgets/lines/batch_add_remarks/', { budget_line_ids, remark_text, remark_template_id });

export const batchSendBackForReview = ({ budget_line_ids, reason }) =>
  api.post('/api/v1/budgets/lines/batch_send_back_for_review/', { budget_line_ids, reason });

export const batchApplyTemplateToCategory = ({ budget_id, category, remark_template_id }) =>
  api.post('/api/v1/budgets/lines/batch_apply_template_to_category/', { budget_id, category, remark_template_id });

export const moderatorApproveLines = ({ budget_line_ids }) =>
  api.post('/api/v1/budgets/lines/batch_moderator_approve/', { budget_line_ids });

// Templates and variance audit
export const fetchRemarkTemplates = (params = {}) => api.get('/api/v1/budgets/remark-templates/', { params });
export const createRemarkTemplate = (payload) => api.post('/api/v1/budgets/remark-templates/', payload);
export const updateRemarkTemplate = (id, payload) => api.patch(`/api/v1/budgets/remark-templates/${id}/`, payload);
export const deleteRemarkTemplate = (id) => api.delete(`/api/v1/budgets/remark-templates/${id}/`);
export const fetchVarianceAudit = (params = {}) => api.get('/api/v1/budgets/variance-audit/', { params });

// Clone budget
export const cloneBudget = (id, payload) => api.post(`/api/v1/budgets/periods/${id}/clone/`, payload);

// Phase 9: AI features
export const fetchLinePricePrediction = (lineId) => api.get(`/api/v1/budgets/lines/${lineId}/price_prediction/`);
export const fetchLineConsumptionForecast = (lineId) => api.get(`/api/v1/budgets/lines/${lineId}/consumption_forecast/`);
export const computeBudgetForecasts = (budgetId) => api.post(`/api/v1/budgets/periods/${budgetId}/compute_forecasts/`);
export const fetchBudgetAlerts = (budgetId) => api.get(`/api/v1/budgets/periods/${budgetId}/alerts/`);


// Phase 10: Gamification
export const fetchBudgetBadges = (budgetId) => api.get(`/api/v1/budgets/periods/${budgetId}/badges/`);
export const fetchLeaderboard = (params = {}) => api.get('/api/v1/budgets/periods/leaderboard/', { params });
export const fetchGamificationKpis = () => api.get('/api/v1/budgets/periods/kpis/');

// Company price policy
export const fetchPricePolicy = () => api.get('/api/v1/budgets/price-policy/');
export const updatePricePolicy = (payload) => api.patch('/api/v1/budgets/price-policy/', payload);

export const rejectApprovalLines = (id, { line_ids }) => api.post(`/api/v1/budgets/approvals/${id}/reject_lines/`, { line_ids });
