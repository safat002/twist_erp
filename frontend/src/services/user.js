import api from './api';

export const fetchCurrentUser = () => api.get('/api/v1/users/me/');

export const updateCurrentUser = (payload) => api.patch('/api/v1/users/me/', payload);
