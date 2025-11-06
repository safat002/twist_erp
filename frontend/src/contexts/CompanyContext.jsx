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
import { organizationalContextService } from '../services/organization';

const CompanyContext = createContext();

export const useCompany = () => useContext(CompanyContext);

export const CompanyProvider = ({ children }) => {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [currentCompany, setCurrentCompany] = useState(null);

  // Enhanced hierarchy state
  const [companyGroups, setCompanyGroups] = useState([]);
  const [branches, setBranches] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [currentGroup, setCurrentGroup] = useState(null);
  const [currentBranch, setCurrentBranch] = useState(null);
  const [currentDepartment, setCurrentDepartment] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fallbackCompanies = useMemo(
    () => [
      {
        id: 1,
        code: 'HQ',
        name: 'Twist HQ (Demo)',
        industry: 'Garments',
        timezone: 'Asia/Dhaka',
      },
      {
        id: 2,
        code: 'PRINT',
        name: 'Twist Printing Unit',
        industry: 'Printing',
        timezone: 'Asia/Dhaka',
      },
      {
        id: 3,
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
    if (!companyId || isNaN(parseInt(companyId, 10))) {
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
      // Primary: full list
      const response = await api.get('/companies/companies/');
      const payload = response.data?.results || response.data || [];
      const hasBackendCompanies = Array.isArray(payload) && payload.length > 0;
      let list = hasBackendCompanies ? payload : [];
      let matched = null;

      if (hasBackendCompanies) {
        try {
          const activeResponse = await api.get('/companies/companies/active/');
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
          list.find((company) => String(company.id) === String(storedId)) || null;
      }

      // Final fallback: pick the first available backend company so the UI has context
      if (!matched && hasBackendCompanies) {
        matched = list[0] || null;
      }

      // If no list returned, try minimal list endpoint (active companies only)
      if (!hasBackendCompanies) {
        try {
          const minimalResp = await api.get('/companies/companies/minimal/');
          const minimal = minimalResp.data || [];
          if (Array.isArray(minimal) && minimal.length) {
            list = minimal;
            matched = minimal[0];
          }
        } catch (_) {
          // ignore, keep empty list
        }
      }

      setCompanies(list.length ? list : []);

      setCurrentCompany(matched || null);
      persistActiveCompany((matched || {}).id);
    } catch (err) {
      console.warn('Failed to load companies:', err?.message);
      setError(err);
      // Try to fetch active company to at least give the UI a context
      try {
        const activeResponse = await api.get('/companies/companies/active/');
        const active = activeResponse?.data;
        if (active) {
          setCompanies([active]);
          setCurrentCompany(active);
          persistActiveCompany(active.id);
        } else {
          setCompanies([]);
          setCurrentCompany(null);
        }
      } catch (_) {
        setCompanies([]);
        setCurrentCompany(null);
      }
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
          const response = await api.post(`/companies/companies//activate/`);
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
      // Avoid full page reload; feature context and components react to company change
    },
    [companies, currentCompany?.id, persistActiveCompany],
  );

  // Load organizational context
  const loadOrganizationalContext = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await organizationalContextService.getCurrent();
      const context = response.data;

      if (context.company_group) {
        setCurrentGroup(context.company_group);
      }
      if (context.branch) {
        setCurrentBranch(context.branch);
      }
      if (context.department) {
        setCurrentDepartment(context.department);
      }
    } catch (err) {
      console.warn('Failed to load organizational context:', err);
    }
  }, [isAuthenticated]);

  // Switch organizational context
  const switchOrganizationalContext = useCallback(async (context) => {
    try {
      await organizationalContextService.updateContext({
        company_group_id: context.groupId || null,
        company_id: context.companyId || null,
        branch_id: context.branchId || null,
        department_id: context.departmentId || null,
      });

      if (context.group) setCurrentGroup(context.group);
      if (context.company) setCurrentCompany(context.company);
      if (context.branch) setCurrentBranch(context.branch);
      if (context.department) setCurrentDepartment(context.department);

      // Update localStorage
      if (context.companyId) {
        persistActiveCompany(context.companyId);
        localStorage.setItem('twist-active-branch', context.branchId || '');
        localStorage.setItem('twist-active-department', context.departmentId || '');
      }
    } catch (err) {
      console.error('Failed to switch organizational context:', err);
    }
  }, [persistActiveCompany]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    hydrateCompanies();
    loadOrganizationalContext();
  }, [authLoading, hydrateCompanies, loadOrganizationalContext]);

  const value = {
    // Existing company-related values
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

    // Enhanced hierarchy values
    companyGroups,
    branches,
    departments,
    currentGroup,
    currentBranch,
    currentDepartment,
    setCurrentGroup,
    setCurrentBranch,
    setCurrentDepartment,
    switchOrganizationalContext,
    loadOrganizationalContext,
  };

  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
};

