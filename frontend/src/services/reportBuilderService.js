import api from './api';

const BASE_URL = '/api/v1/report-builder';

export const listReportDefinitions = (params = {}) =>
  api.get(`${BASE_URL}/definitions/`, { params });

export const getReportDefinition = (id) =>
  api.get(`${BASE_URL}/definitions/${id}/`);

export const createReportDefinition = (payload) =>
  api.post(`${BASE_URL}/definitions/`, payload);

export const updateReportDefinition = (id, payload) =>
  api.put(`${BASE_URL}/definitions/${id}/`, payload);

export const deleteReportDefinition = (id) =>
  api.delete(`${BASE_URL}/definitions/${id}/`);

export const publishReportDefinition = (id) =>
  api.post(`${BASE_URL}/definitions/${id}/publish/`);

export const listReportDatasets = () =>
  api.get(`${BASE_URL}/definitions/datasets/`);

export const previewReportDefinition = (id, payload) =>
  api.post(`${BASE_URL}/definitions/${id}/preview/`, payload);

export default {
  listReportDefinitions,
  getReportDefinition,
  createReportDefinition,
  updateReportDefinition,
  deleteReportDefinition,
  publishReportDefinition,
  listReportDatasets,
  previewReportDefinition,
};
