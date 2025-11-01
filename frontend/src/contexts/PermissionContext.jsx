import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import api from '../services/api';

const PermissionContext = createContext(null);

export const PermissionProvider = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const [permissions, setPermissions] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPermissions = async () => {
      if (isAuthenticated && user) {
        setLoading(true);
        try {
          // Permissions are now part of the user object fetched by AuthContext
          // We can directly use user.effective_permissions
          setPermissions(user.effective_permissions || {});
        } catch (error) {
          console.error("Failed to fetch permissions:", error);
          setPermissions({});
        } finally {
          setLoading(false);
        }
      } else {
        setPermissions({});
        setLoading(false);
      }
    };

    fetchPermissions();
  }, [isAuthenticated, user]);

  // Helper function to check if user has a permission
  const can = (permCode, recordScope = null) => {
    if (loading) return false; // Or handle as needed during loading
    if (!permissions || !permissions[permCode]) return false;

    const allowedScopes = permissions[permCode];

    // If permission is global for the user
    if (allowedScopes.has('*')) {
      return true;
    }

    // If permission requires a specific scope and it's provided
    if (recordScope) {
      return allowedScopes.has(recordScope);
    }

    // If permission requires scope but no recordScope provided, or no global permission
    return false;
  };

  return (
    <PermissionContext.Provider value={{ permissions, loading, can }}>
      {children}
    </PermissionContext.Provider>
  );
};

export const usePermissions = () => useContext(PermissionContext);

export const useCan = (permCode, recordScope = null) => {
  const { can } = usePermissions();
  return can(permCode, recordScope);
};
