import React from 'react';
import { Row, Col, Card, Statistic, Progress, Typography, Space, Tooltip } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

/**
 * InventoryStats - KPI cards component for displaying key metrics
 * Supports trends, progress bars, and custom formatting
 */
const InventoryStats = ({ stats = [], loading = false, gutter = 16 }) => {
  const renderStatValue = (stat) => {
    // If custom renderer provided, use it
    if (stat.render) {
      return stat.render(stat);
    }

    // Default rendering
    return (
      <Statistic
        title={
          <Space>
            {stat.title}
            {stat.tooltip && (
              <Tooltip title={stat.tooltip}>
                <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
              </Tooltip>
            )}
          </Space>
        }
        value={stat.value}
        precision={stat.precision || 0}
        valueStyle={{
          color: stat.color || (stat.status === 'danger' ? '#cf1322' : stat.status === 'warning' ? '#faad14' : stat.status === 'success' ? '#3f8600' : '#262626'),
          fontSize: stat.fontSize || 24,
        }}
        prefix={stat.prefix}
        suffix={stat.suffix}
      />
    );
  };

  const renderTrend = (stat) => {
    if (!stat.trend && stat.trend !== 0) return null;

    const isPositive = stat.trend > 0;
    const isNegative = stat.trend < 0;

    // Determine if positive trend is good or bad
    const isGoodTrend = stat.trendInverse ? isNegative : isPositive;

    return (
      <div style={{ marginTop: 8 }}>
        <Text
          type={isGoodTrend ? 'success' : isNegative || isPositive ? 'danger' : 'secondary'}
          style={{ fontSize: 12 }}
        >
          {isPositive ? <ArrowUpOutlined /> : isNegative ? <ArrowDownOutlined /> : null}
          <span style={{ marginLeft: 4 }}>
            {Math.abs(stat.trend)}% {stat.trendLabel || 'vs last period'}
          </span>
        </Text>
      </div>
    );
  };

  const renderProgress = (stat) => {
    if (!stat.progress && stat.progress !== 0) return null;

    let status = 'normal';
    let strokeColor;

    if (stat.progress >= 90) {
      status = 'success';
      strokeColor = '#52c41a';
    } else if (stat.progress >= 70) {
      status = 'normal';
      strokeColor = '#1890ff';
    } else if (stat.progress >= 50) {
      status = 'normal';
      strokeColor = '#faad14';
    } else {
      status = 'exception';
      strokeColor = '#ff4d4f';
    }

    return (
      <div style={{ marginTop: 12 }}>
        <Progress
          percent={stat.progress}
          status={status}
          strokeColor={strokeColor}
          size="small"
          format={(percent) => `${percent}%`}
        />
        {stat.progressLabel && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {stat.progressLabel}
          </Text>
        )}
      </div>
    );
  };

  const getCardStyle = (stat) => {
    const baseStyle = {
      borderRadius: 8,
      height: '100%',
    };

    if (stat.highlight) {
      return {
        ...baseStyle,
        borderLeft: `4px solid ${stat.highlightColor || '#1890ff'}`,
      };
    }

    return baseStyle;
  };

  return (
    <Row gutter={gutter} style={{ marginBottom: 24 }}>
      {stats.map((stat, index) => (
        <Col
          key={stat.key || index}
          xs={24}
          sm={12}
          md={stat.span || 6}
          lg={stat.span || 6}
        >
          <Card
            loading={loading}
            bordered={true}
            hoverable={stat.onClick ? true : false}
            onClick={stat.onClick}
            style={getCardStyle(stat)}
            bodyStyle={{ padding: '20px' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              {stat.icon && (
                <div
                  style={{
                    fontSize: 32,
                    color: stat.iconColor || '#1890ff',
                    marginRight: 16,
                    flexShrink: 0,
                  }}
                >
                  {stat.icon}
                </div>
              )}
              <div style={{ flex: 1 }}>
                {renderStatValue(stat)}
                {renderTrend(stat)}
                {renderProgress(stat)}
                {stat.footer && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {stat.footer}
                    </Text>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
};

/**
 * StatCard - Single stat card component (can be used independently)
 */
export const StatCard = ({
  title,
  value,
  suffix,
  prefix,
  trend,
  trendInverse = false,
  trendLabel,
  icon,
  iconColor,
  color,
  status,
  progress,
  progressLabel,
  onClick,
  tooltip,
  footer,
  highlight = false,
  highlightColor,
  loading = false,
}) => {
  return (
    <InventoryStats
      stats={[
        {
          title,
          value,
          suffix,
          prefix,
          trend,
          trendInverse,
          trendLabel,
          icon,
          iconColor,
          color,
          status,
          progress,
          progressLabel,
          onClick,
          tooltip,
          footer,
          highlight,
          highlightColor,
        },
      ]}
      loading={loading}
      gutter={0}
    />
  );
};

export default InventoryStats;
