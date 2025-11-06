import { useEffect, useMemo, useState } from 'react';
import api from '../services/api';

export default function usePermissions() {
  const [perms, setPerms] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const { data } = await api.get('/api/v1/users/me/');
        const effective = data?.effective_permissions || {};
        if (mounted) setPerms(effective);
      } catch (e) {
        if (mounted) setPerms({});
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, []);

  const can = useMemo(
    () => (code) => {
      if (!code) return false;
      const scope = perms?.[code];
      if (!scope) return false;
      // If global or any scope exists, allow
      if (scope === '*' || (Array.isArray(scope) && scope.length > 0)) return true;
      if (typeof scope === 'object') return Object.keys(scope || {}).length > 0;
      return !!scope;
    },
    [perms],
  );

  return { can, loading, raw: perms };
}

