import React from 'react';
import { Navigate } from 'react-router-dom';
import { useFeatures } from '../../contexts/FeatureContext';
import { Spin, Alert, Typography } from 'antd';

const { Text } = Typography;

/**
 * Component to guard routes based on feature toggles
 */
export const FeatureGuard = ({
  module,
  feature = 'module',
  children,
  fallback = null,
  redirectTo = '/',
  showLoading = true,
  showError = true,
}) => {
  const { isFeatureEnabled, loading, error } = useFeatures();

  // Show loading state
  if (loading && showLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <Spin size="large" />
        <Text type="secondary">Loading features...</Text>
      </div>
    );
  }

  // Show error state
  if (error && showError) {
    return (
      <div style={{ padding: '24px' }}>
        <Alert
          message="Failed to load feature configuration"
          description={
            <>
              Please refresh the page or contact support if the issue persists.
              <br />
              <small>{error}</small>
            </>
          }
          type="error"
          showIcon
        />
      </div>
    );
  }

  // Check if feature is enabled
  const enabled = isFeatureEnabled(module, feature);

  if (!enabled) {
    if (fallback) {
      return fallback;
    }

    // Redirect to dashboard or specified route
    return <Navigate to={redirectTo} replace />;
  }

  // Feature is enabled - render children
  return <>{children}</>;
};

export default FeatureGuard;
