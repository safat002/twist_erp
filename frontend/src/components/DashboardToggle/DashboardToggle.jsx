import React, { useState } from 'react';
import { Switch, Tooltip, message } from 'antd';
import { LockOutlined, UnlockOutlined } from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { useFeatures } from '../../contexts/FeatureContext';

/**
 * Dashboard Toggle Switch - Admin-only feature toggle in dashboard cards
 *
 * @param {string} module - Module name (e.g., 'finance')
 * @param {string} feature - Feature key (default: 'module')
 * @param {string} label - Display label for the toggle
 */
const DashboardToggle = ({ module, feature = 'module', label }) => {
  const { user } = useAuth();
  const { isFeatureEnabled, toggleFeature, loading } = useFeatures();
  const [toggling, setToggling] = useState(false);

  // Only show to admin users
  if (!user?.is_staff) {
    return null;
  }

  const enabled = isFeatureEnabled(module, feature);
  const featureName = label || `${module}.${feature}`;

  const handleToggle = async (checked) => {
    setToggling(true);
    try {
      await toggleFeature(module, feature, checked);
      message.success(`${featureName} ${checked ? 'enabled' : 'disabled'} successfully`);
    } catch (error) {
      message.error(`Failed to toggle ${featureName}: ${error.message}`);
      console.error('Toggle error:', error);
    } finally {
      setToggling(false);
    }
  };

  return (
    <Tooltip
      title={enabled ? 'Click to disable this feature' : 'Click to enable this feature'}
      placement="left"
    >
      <Switch
        checked={enabled}
        onChange={handleToggle}
        loading={toggling || loading}
        size="small"
        checkedChildren={<UnlockOutlined />}
        unCheckedChildren={<LockOutlined />}
        style={{
          marginLeft: 8,
        }}
      />
    </Tooltip>
  );
};

export default DashboardToggle;
