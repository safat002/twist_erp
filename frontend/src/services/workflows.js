import api from './api';

const workflowService = {
  // Templates
  listTemplates(params = {}) {
    return api.get('/api/v1/workflows/templates/', { params }).then(r => r.data?.results || r.data || []);
  },
  createTemplate(payload) {
    return api.post('/api/v1/workflows/templates/', payload).then(r => r.data);
  },
  // Instances
  listInstances(params = {}) {
    return api.get('/api/v1/workflows/instances/', { params }).then(r => r.data?.results || r.data || []);
  },
  createInstance(payload) {
    return api.post('/api/v1/workflows/instances/', payload).then(r => r.data);
  },
  transitionInstance(instanceId, toState) {
    return api.post(`/api/v1/workflows/instances/${instanceId}/transition/`, { to: toState }).then(r => r.data);
  },
  approveInstance(instanceId) {
    return api.post(`/api/v1/workflows/instances/${instanceId}/approve/`).then(r => r.data);
  },
};

export default workflowService;

