import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import api from '../services/api';
import { useAuth } from './AuthContext';

const CompanyContext = createContext();

export const useCompany = () => useContext(CompanyContext);

export const CompanyProvider = ({ children }) => {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [currentCompany, setCurrentCompany] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fallbackCompanies = useMemo(
    () => [
      {
        id: 'demo-hq',
        code: 'HQ',
        name: 'Twist HQ (Demo)',
        industry: 'Garments',
        timezone: 'Asia/Dhaka',
      },
      {
        id: 'demo-print',
        code: 'PRINT',
        name: 'Twist Printing Unit',
        industry: 'Printing',
        timezone: 'Asia/Dhaka',
      },
      {
        id: 'demo-eu',
        code: 'EU',
        name: 'Twist Europe',
        industry: 'Distribution',
        timezone: 'Europe/Berlin',
      },
    ],
    [],
  );

  const persistActiveCompany = useCallback((companyId) => {
    if (typeof window === 'undefined') {
      return;
    }
    if (!companyId) {
      window.localStorage.removeItem('twist-active-company');
      return;
    }
    window.localStorage.setItem('twist-active-company', String(companyId));
  }, []);

  const loadFromStorage = useCallback(() => {
    if (typeof window === 'undefined') {
      return null;
    }
    return window.localStorage.getItem('twist-active-company');
  }, []);

  const applyFallbackCompanies = useCallback(() => {
    setCompanies(fallbackCompanies);
    const storedId = loadFromStorage();
    const matched =
      fallbackCompanies.find((company) => String(company.id) === String(storedId)) ||
      fallbackCompanies[0] ||
      null;
    setCurrentCompany(matched);
    persistActiveCompany(matched?.id);
  }, [fallbackCompanies, loadFromStorage, persistActiveCompany]);

  const hydrateCompanies = useCallback(async () => {
    setLoading(true);
    setError(null);

    if (!isAuthenticated) {
      applyFallbackCompanies();
      setLoading(false);
      return;
    }

    try {
      const response = await api.get('/api/v1/companies/');
      const payload = response.data?.results || response.data || [];
      const hasBackendCompanies = Array.isArray(payload) && payload.length > 0;
      const list = hasBackendCompanies ? payload : fallbackCompanies;
      setCompanies(list);
      let matched = null;

      if (hasBackendCompanies) {
        try {
          const activeResponse = await api.get('/api/v1/companies/active/');
          const activeData = activeResponse.data;
          if (activeData) {
            matched =
              list.find((company) => String(company.id) === String(activeData.id)) ||
              activeData ||
              null;
          }
        } catch (activeErr) {
          console.warn('Unable to fetch active company from backend:', activeErr?.message);
        }
      }

      if (!matched) {
        const storedId = loadFromStorage();
        matched =
          list.find((company) => String(company.id) === String(storedId)) || list[0] || null;
      }

      setCurrentCompany(matched);
      persistActiveCompany(matched?.id);
    } catch (err) {
      console.warn('Failed to load companies, using fallback list:', err?.message);
      setError(err);
      applyFallbackCompanies();
    } finally {
      setLoading(false);
    }
  }, [
    applyFallbackCompanies,
    fallbackCompanies,
    isAuthenticated,
    loadFromStorage,
    persistActiveCompany,
  ]);

  const switchCompany = useCallback(
    async (companyId, { forceRefresh = false } = {}) => {
      if (!companyId || String(companyId) === String(currentCompany?.id)) {
        return;
      }
      let targetCompany =
        companies.find((company) => String(company.id) === String(companyId)) || null;

      const isBackendCompany =
        targetCompany && !Number.isNaN(Number(targetCompany.id)) && Number(targetCompany.id) > 0;

      if (isBackendCompany) {
        try {
          const response = await api.post(`/api/v1/companies/${companyId}/activate/`);
          if (response?.data) {
            targetCompany = response.data;
            setCompanies((prev) => {
              const exists = prev.some(
                (company) => String(company.id) === String(targetCompany.id),
              );
              if (!exists) {
                return prev;
              }
              return prev.map((company) =>
                String(company.id) === String(targetCompany.id)
                  ? { ...company, ...targetCompany }
                  : company,
              );
            });
          }
        } catch (err) {
          console.warn('Company switch request failed, applying client-side only:', err?.message);
        }
      }

      setCurrentCompany(targetCompany);
      persistActiveCompany(targetCompany?.id);
      if (forceRefresh && typeof window !== 'undefined') {
        window.location.reload();
      }
    },
    [companies, currentCompany?.id, persistActiveCompany],
  );

  useEffect(() => {
    if (authLoading) {
      return;
    }
    hydrateCompanies();
  }, [authLoading, hydrateCompanies]);

  const value = {
    companies,
    currentCompany,
    loading,
    error,
    switchCompany,
    refreshCompanies: hydrateCompanies,
    setCurrentCompany: (company) => {
      setCurrentCompany(company);
      persistActiveCompany(company?.id);
    },
  };

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
};
