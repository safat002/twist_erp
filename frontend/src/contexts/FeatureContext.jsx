import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useCompany } from './CompanyContext';
import api from '../services/api';

const FeatureContext = createContext();

export const FeatureProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const { currentCompany } = useCompany();

  const [features, setFeatures] = useState({});
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastFetched, setLastFetched] = useState(null);

  const fetchFeatures = useCallback(async () => {
    if (!isAuthenticated) {
      setFeatures({});
      setModules([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get('/api/v1/admin-settings/features/');

      setFeatures(response.data.features || {});
      setModules(response.data.modules || []);
      setLastFetched(new Date());

      // Cache in localStorage with TTL
      const cacheData = {
        features: response.data.features,
        modules: response.data.modules,
        timestamp: Date.now(),
        company: currentCompany?.id,
      };
      localStorage.setItem('feature_cache', JSON.stringify(cacheData));

      console.log('✓ Features loaded:', {
        count: Object.keys(response.data.features).length,
        modules: response.data.modules,
        scope: response.data.scope,
        cached: response.data.cached,
      });
    } catch (err) {
      console.error('Failed to fetch features:', err);
      setError(err.message);

      // Try to load from cache on error
      try {
        const cached = localStorage.getItem('feature_cache');
        if (cached) {
          const cacheData = JSON.parse(cached);
          const age = Date.now() - cacheData.timestamp;
          const maxAge = 10 * 60 * 1000; // 10 minutes

          if (age < maxAge && cacheData.company === currentCompany?.id) {
            setFeatures(cacheData.features || {});
            setModules(cacheData.modules || []);
            console.log('Using cached features (API failed)');
          }
        }
      } catch (cacheErr) {
        console.error('Failed to load cached features:', cacheErr);
      }
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, currentCompany]);

  // Fetch on auth or company change
  useEffect(() => {
    fetchFeatures();
  }, [fetchFeatures]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      console.log('Auto-refreshing features...');
      fetchFeatures();
    }, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated, fetchFeatures]);

  /**
   * Check if a feature is enabled
   * @param {string} moduleKey - Module name (e.g., 'finance')
   * @param {string} featureKey - Feature key (e.g., 'journal_vouchers')
   * @returns {boolean}
   */
  const isFeatureEnabled = useCallback((moduleKey, featureKey = 'module') => {
    if (loading) return false; // Deny access while loading

    const key = `${moduleKey}.${featureKey}`;
    const feature = features[key];

    return feature?.enabled ?? false;
  }, [features, loading]);

  /**
   * Check if a feature is visible in menus
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @returns {boolean}
   */
  const isFeatureVisible = useCallback((moduleKey, featureKey = 'module') => {
    if (loading) return false;

    const key = `${moduleKey}.${featureKey}`;
    const feature = features[key];

    return feature?.visible ?? false;
  }, [features, loading]);

  /**
   * Check if an entire module is enabled
   * @param {string} moduleKey - Module name
   * @returns {boolean}
   */
  const isModuleEnabled = useCallback((moduleKey) => {
    return isFeatureEnabled(moduleKey, 'module');
  }, [isFeatureEnabled]);

  /**
   * Get feature metadata
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @returns {object|null}
   */
  const getFeature = useCallback((moduleKey, featureKey = 'module') => {
    const key = `${moduleKey}.${featureKey}`;
    return features[key] || null;
  }, [features]);

  /**
   * Check if all dependencies are met for a feature
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @returns {boolean}
   */
  const areDependenciesMet = useCallback((moduleKey, featureKey = 'module') => {
    const feature = getFeature(moduleKey, featureKey);

    if (!feature || !feature.depends_on || feature.depends_on.length === 0) {
      return true; // No dependencies
    }

    return feature.depends_on.every(depKey => {
      const [depModule, depFeature] = depKey.split('.');
      return isFeatureEnabled(depModule, depFeature || 'module');
    });
  }, [getFeature, isFeatureEnabled]);

  /**
   * Get list of enabled module names
   * @returns {string[]}
   */
  const getEnabledModules = useCallback(() => {
    return modules;
  }, [modules]);

  /**
   * Manually refresh features (e.g., after admin changes)
   */
  const refreshFeatures = useCallback(() => {
    return fetchFeatures();
  }, [fetchFeatures]);

  /**
   * Toggle a feature on/off (admin only)
   * @param {string} moduleKey - Module name
   * @param {string} featureKey - Feature key
   * @param {boolean} enabled - New enabled state
   * @returns {Promise}
   */
  const toggleFeature = useCallback(async (moduleKey, featureKey, enabled) => {
    try {
      const response = await api.post(
        `/api/v1/admin-settings/features/${moduleKey}/${featureKey}/toggle/`,
        { is_enabled: enabled }
      );

      // Refresh features to get updated state
      await fetchFeatures();

      return response.data;
    } catch (err) {
      console.error('Failed to toggle feature:', err);
      throw err;
    }
  }, [fetchFeatures]);

  const value = {
    // State
    features,
    modules,
    loading,
    error,
    lastFetched,

    // Functions
    isFeatureEnabled,
    isFeatureVisible,
    isModuleEnabled,
    getFeature,
    areDependenciesMet,
    getEnabledModules,
    refreshFeatures,
    toggleFeature,
  };

  return (
    <FeatureContext.Provider value={value}>
      {children}
    </FeatureContext.Provider>
  );
};

/**
 * Hook to access feature context
 * @returns {object}
 */
export const useFeatures = () => {
  const context = useContext(FeatureContext);

  if (!context) {
    throw new Error('useFeatures must be used within a FeatureProvider');
  }

  return context;
};

/**
 * Hook to check if a feature is enabled (convenience hook)
 * @param {string} moduleKey - Module name
 * @param {string} featureKey - Feature key (default: 'module')
 * @returns {boolean}
 */
export const useFeatureEnabled = (moduleKey, featureKey = 'module') => {
  const { isFeatureEnabled } = useFeatures();
  return isFeatureEnabled(moduleKey, featureKey);
};

/**
 * Hook to check if a module is enabled (convenience hook)
 * @param {string} moduleKey - Module name
 * @returns {boolean}
 */
export const useModuleEnabled = (moduleKey) => {
  const { isModuleEnabled } = useFeatures();
  return isModuleEnabled(moduleKey);
};

export default FeatureContext;
