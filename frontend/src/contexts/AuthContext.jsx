import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import axios from 'axios';
import api from '../services/api';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8788/api/v1';

const base64UrlDecode = (input) => {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized.padEnd(normalized.length + (4 - (normalized.length % 4)) % 4, '=');
  if (typeof window !== 'undefined' && typeof window.atob === 'function') {
    return window.atob(padded);
  }
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(padded, 'base64').toString('binary');
  }
  throw new Error('No base64 decoder available');
};

export const AuthProvider = ({ children }) => {
  const [authToken, setAuthToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);

  const clearStoredTokens = useCallback(() => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setAuthToken(null);
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  const verifyAccessToken = useCallback(async (token) => {
    if (!token) {
      return false;
    }
    try {
      const [, payloadSegment] = token.split('.');
      if (!payloadSegment) {
        return false;
      }
      const decodedPayload = base64UrlDecode(payloadSegment);
      const decoded = JSON.parse(
        decodeURIComponent(
          decodedPayload
            .split('')
            .map((char) => `%${(`00${char.charCodeAt(0).toString(16)}`).slice(-2)}`)
            .join(''),
        ),
      );
      if (!decoded?.exp) {
        return false;
      }
      const now = Math.floor(Date.now() / 1000);
      // Refresh proactively if the token expires within the next 30 seconds
      return decoded.exp > now + 30;
    } catch (_err) {
      return false;
    }
  }, []);

  const refreshAccessToken = useCallback(async (refreshToken) => {
    if (!refreshToken) {
      return null;
    }
    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      });
      if (data?.access) {
        localStorage.setItem('accessToken', data.access);
        return data.access;
      }
    } catch (error) {
      console.warn('Failed to refresh access token:', error?.message || error);
    }
    return null;
  }, []);

  const fetchUserProfile = useCallback(async () => {
    try {
      setProfileLoading(true);
      const { data } = await api.get('/api/v1/users/me/');
      setUser(data);
      return data;
    } catch (error) {
      console.warn('Failed to load user profile:', error?.message || error);
      return null;
    } finally {
      setProfileLoading(false);
    }
  }, []);

  const syncStoredTokens = useCallback(async () => {
    const accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');

    if (!accessToken || !refreshToken) {
      clearStoredTokens();
      setLoading(false);
      return;
    }

    let activeAccessToken = accessToken;
    let isValid = await verifyAccessToken(accessToken);

    if (!isValid) {
      activeAccessToken = await refreshAccessToken(refreshToken);
      isValid = Boolean(activeAccessToken);
    }

    if (isValid && activeAccessToken) {
      setAuthToken({ access: activeAccessToken, refresh: refreshToken });
      const fetchedUser = await fetchUserProfile();
      if (fetchedUser) {
        setIsAuthenticated(true);
      } else {
        clearStoredTokens();
      }
    } else {
      clearStoredTokens();
    }

    setLoading(false);
  }, [clearStoredTokens, fetchUserProfile, refreshAccessToken, verifyAccessToken]);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/token/`, {
        username,
        password,
      });
      const { access, refresh } = response.data;
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      setAuthToken({ access, refresh });
      const fetchedUser = await fetchUserProfile();
      if (!fetchedUser) {
        clearStoredTokens();
        return false;
      }
      setIsAuthenticated(true);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      clearStoredTokens();
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = useCallback(() => {
    clearStoredTokens();
  }, [clearStoredTokens]);

  useEffect(() => {
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        if (authToken?.access) {
          config.headers.Authorization = `Bearer ${authToken.access}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
    };
  }, [authToken]);

  useEffect(() => {
    syncStoredTokens();
  }, [syncStoredTokens]);

  useEffect(() => {
      const handler = (event) => {
      const { access, refresh } = event.detail || {};
      if (access) {
        const refreshToken = refresh || localStorage.getItem('refreshToken');
        setAuthToken({ access, refresh: refreshToken });
        setIsAuthenticated(true);
        fetchUserProfile();
      } else {
        clearStoredTokens();
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('twist-auth-updated', handler);
    }

    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('twist-auth-updated', handler);
      }
    };
  }, [clearStoredTokens, fetchUserProfile]);

  const updateProfile = useCallback(
    async (updates) => {
      const { data } = await api.patch('/api/v1/users/me/', updates);
      setUser(data);
      return data;
    },
    [],
  );

  const value = {
    isAuthenticated,
    user,
    loading,
    profileLoading,
    login,
    logout,
    authToken,
    refreshProfile: fetchUserProfile,
    updateProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
