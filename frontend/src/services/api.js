import axios from 'axios';

// Helper to read cookie value (for CSRF)
function getCookie(name) {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// Base API root used for auth and normalization
const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL && String(import.meta.env.VITE_API_BASE_URL).trim()) || '/api/v1';

const api = axios.create({
  withCredentials: false,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      // eslint-disable-next-line no-param-reassign
      config.headers.Authorization = `Bearer ${token}`;
    }
    const companyId = localStorage.getItem('twist-active-company');
    if (companyId) {
      // eslint-disable-next-line no-param-reassign
      config.headers['X-Company-ID'] = companyId;
    }

    // Normalize URL to avoid double /api/v1 and to prefix missing base
    try {
      let url = config.url || '';
      if (typeof url === 'string' && !/^https?:\/\//i.test(url)) {
        const base = String(API_BASE_URL || '/api/v1').replace(/\/$/, '');

        // If already starts with /api or /api/v1 keep as-is, else prefix base
        if (/^\/(api|api\/v1)\//.test(url)) {
          // no-op
        } else if (url.startsWith('/')) {
          url = `${base}${url}`;
        } else {
          url = `${base}/${url}`;
        }

        // Collapse accidental double prefixes and duplicate slashes (but not protocol)
        url = url.replace(/\/api\/v1\/api\/v1\/?/g, '/api/v1/');
        url = url.replace(/([^:])\/\/+/, '$1/');

        // eslint-disable-next-line no-param-reassign
        config.url = url;
      }
    } catch (_) {
      // leave config.url unchanged on any normalization error
    }

    // Attach CSRF token for unsafe methods when available (SessionAuthentication)
    try {
      const method = (config.method || 'get').toLowerCase();
      if (!['get', 'head', 'options'].includes(method)) {
        const csrf = getCookie('csrftoken');
        if (csrf && !config.headers['X-CSRFToken']) {
          // eslint-disable-next-line no-param-reassign
          config.headers['X-CSRFToken'] = csrf;
        }
      }
    } catch (_) {}

    return config;
  },
  (error) => Promise.reject(error),
);

let isRefreshing = false;
const refreshQueue = [];

const processQueue = (error, token = null) => {
  while (refreshQueue.length > 0) {
    const { resolve, reject } = refreshQueue.shift();
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  }
};

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  if (!refreshToken) {
    return null;
  }
  const url = `${API_BASE_URL.replace(/\/$/, '')}/auth/token/refresh/`;
  const response = await axios.post(url, { refresh: refreshToken });
  const newAccess = response?.data?.access;
  if (newAccess) {
    localStorage.setItem('accessToken', newAccess);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('twist-auth-updated', {
          detail: { access: newAccess, refresh: refreshToken },
        }),
      );
    }
  }
  return newAccess;
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const originalRequest = error?.config;

    if (status !== 401 || !originalRequest || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (!localStorage.getItem('refreshToken')) {
      console.warn('No refresh token available; clearing stored credentials.');
      localStorage.removeItem('accessToken');
      return Promise.reject(error);
    }

    originalRequest._retry = true; // eslint-disable-line no-underscore-dangle

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push({
          resolve: (token) => {
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            } else {
              reject(error);
            }
          },
          reject,
        });
      });
    }

    isRefreshing = true;

    return new Promise((resolve, reject) => {
      refreshAccessToken()
        .then((newToken) => {
          if (!newToken) {
            throw new Error('Unable to refresh access token.');
          }
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          processQueue(null, newToken);
          resolve(api(originalRequest));
        })
        .catch((refreshError) => {
          console.warn('API request unauthorised and refresh failed. Clearing session.');
          processQueue(refreshError, null);
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          if (typeof window !== 'undefined') {
            window.dispatchEvent(
              new CustomEvent('twist-auth-updated', {
                detail: { access: null, refresh: null },
              }),
            );
          }
          reject(refreshError);
        })
        .finally(() => {
          isRefreshing = false;
        });
    });
  },
);

export default api;
