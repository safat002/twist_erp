import api from './api';

export const searchUsers = (params = {}) => api.get('/api/v1/users/lookup/', { params });
