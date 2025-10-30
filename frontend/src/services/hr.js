import api from './api';

const unwrap = (response) => {
  const payload = response?.data;
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload?.results && Array.isArray(payload.results)) {
    return payload.results;
  }
  return payload;
};

export const fetchDepartments = async (companyId) => {
  const response = await api.get('/api/v1/hr/departments/', {
    params: companyId ? { company: companyId } : undefined,
  });
  return unwrap(response);
};

export const fetchEmploymentGrades = async (companyId) => {
  const response = await api.get('/api/v1/hr/grades/', {
    params: companyId ? { company: companyId } : undefined,
  });
  return unwrap(response);
};

export const fetchSalaryStructures = async (companyId) => {
  const response = await api.get('/api/v1/hr/salary-structures/', {
    params: companyId ? { company: companyId } : undefined,
  });
  return unwrap(response);
};

export const fetchEmployees = async (params = {}) => {
  const response = await api.get('/api/v1/hr/employees/', { params });
  return unwrap(response);
};

export const createEmployee = async (payload) => {
  const response = await api.post('/api/v1/hr/employees/', payload);
  return response.data;
};

export const updateEmployee = async (id, payload) => {
  const response = await api.patch(`/api/v1/hr/employees/${id}/`, payload);
  return response.data;
};

export const fetchAttendance = async (params = {}) => {
  const response = await api.get('/api/v1/hr/attendance/', { params });
  return unwrap(response);
};

export const markAttendance = async (payload) => {
  const response = await api.post('/api/v1/hr/attendance/', payload);
  return response.data;
};

export const fetchPayrollRuns = async (params = {}) => {
  const response = await api.get('/api/v1/hr/payroll-runs/', { params });
  return unwrap(response);
};

export const createPayrollRun = async (payload) => {
  const response = await api.post('/api/v1/hr/payroll-runs/', payload);
  return response.data;
};

export const finalizePayrollRun = async (id, payload) => {
  const response = await api.post(`/api/v1/hr/payroll-runs/${id}/finalize/`, payload);
  return response.data;
};

export const cancelPayrollRun = async (id) => {
  await api.delete(`/api/v1/hr/payroll-runs/${id}/`);
};

export const fetchShiftTemplates = async (params = {}) => {
  const response = await api.get('/api/v1/hr/shift-templates/', { params });
  return unwrap(response);
};

export const createShiftTemplate = async (payload) => {
  const response = await api.post('/api/v1/hr/shift-templates/', payload);
  return response.data;
};

export const updateShiftTemplate = async (id, payload) => {
  const response = await api.patch(`/api/v1/hr/shift-templates/${id}/`, payload);
  return response.data;
};

export const fetchShiftAssignments = async (params = {}) => {
  const response = await api.get('/api/v1/hr/shift-assignments/', { params });
  return unwrap(response);
};

export const createShiftAssignment = async (payload) => {
  const response = await api.post('/api/v1/hr/shift-assignments/', payload);
  return response.data;
};

export const updateShiftAssignment = async (id, payload) => {
  const response = await api.patch(`/api/v1/hr/shift-assignments/${id}/`, payload);
  return response.data;
};

export const fetchOvertimePolicies = async (params = {}) => {
  const response = await api.get('/api/v1/hr/overtime-policies/', { params });
  return unwrap(response);
};

export const createOvertimePolicy = async (payload) => {
  const response = await api.post('/api/v1/hr/overtime-policies/', payload);
  return response.data;
};

export const updateOvertimePolicy = async (id, payload) => {
  const response = await api.patch(`/api/v1/hr/overtime-policies/${id}/`, payload);
  return response.data;
};

export const fetchOvertimeEntries = async (params = {}) => {
  const response = await api.get('/api/v1/hr/overtime-entries/', { params });
  return unwrap(response);
};

export const createOvertimeEntry = async (payload) => {
  const response = await api.post('/api/v1/hr/overtime-entries/', payload);
  return response.data;
};

export const updateOvertimeEntry = async (id, payload) => {
  const response = await api.patch(`/api/v1/hr/overtime-entries/${id}/`, payload);
  return response.data;
};

export const submitOvertimeEntry = async (id) => {
  const response = await api.post(`/api/v1/hr/overtime-entries/${id}/submit/`);
  return response.data;
};

export const approveOvertimeEntry = async (id, payload = {}) => {
  const response = await api.post(`/api/v1/hr/overtime-entries/${id}/approve/`, payload);
  return response.data;
};

export const rejectOvertimeEntry = async (id, payload = {}) => {
  const response = await api.post(`/api/v1/hr/overtime-entries/${id}/reject/`, payload);
  return response.data;
};

export const cancelOvertimeEntry = async (id) => {
  const response = await api.post(`/api/v1/hr/overtime-entries/${id}/cancel/`);
  return response.data;
};

export const fetchCapacityPlans = async (params = {}) => {
  const response = await api.get('/api/v1/hr/capacity-plans/', { params });
  return unwrap(response);
};

export const fetchCapacityPlanSummary = async (params = {}) => {
  const response = await api.get('/api/v1/hr/capacity-plans/summary/', { params });
  return response.data;
};
