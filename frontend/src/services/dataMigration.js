import api from './api';

export const listMigrationJobs = (params) =>
  api.get('/api/v1/data-migration/jobs/', { params });

export const getMigrationJob = (jobId) =>
  api.get(`/api/v1/data-migration/jobs/${jobId}/`);

export const createMigrationJob = (payload) =>
  api.post('/api/v1/data-migration/jobs/', payload);

export const uploadMigrationFile = (jobId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/api/v1/data-migration/jobs/${jobId}/upload-file/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const profileMigrationJob = (jobId, options = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/profile/`, null, {
    params: options,
  });

export const stageMigrationJob = (jobId, options = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/stage/`, null, {
    params: options,
  });

export const validateMigrationJob = (jobId, options = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/validate/`, null, {
    params: options,
  });

export const submitMigrationJob = (jobId) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/submit/`);

export const approveMigrationJob = (jobId, payload = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/approve/`, payload);

export const rejectMigrationJob = (jobId, payload = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/reject/`, payload);

export const commitMigrationJob = (jobId, options = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/commit/`, null, { params: options });

export const rollbackMigrationJob = (jobId, options = {}) =>
  api.post(`/api/v1/data-migration/jobs/${jobId}/rollback/`, null, { params: options });

export const updateMapping = (jobId, mappingId, payload) =>
  api.patch(`/api/v1/data-migration/jobs/${jobId}/mappings/${mappingId}/`, payload);
