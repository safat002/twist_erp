import React, { useMemo, useState } from 'react';
import { Table, Switch, Tag, Input, Select, Space, Typography, Tooltip, Button, Modal } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useFeatures } from '../../contexts/FeatureContext';

const { Text } = Typography;

const FeatureToggleManager = () => {
  const { features, loading, toggleFeature, refreshFeatures } = useFeatures();
  const [query, setQuery] = useState('');
  const [moduleFilter, setModuleFilter] = useState('ALL');

  const data = useMemo(() => {
    const rows = Object.entries(features || {}).map(([fullKey, meta]) => {
      const [module, feature] = fullKey.split('.');
      return {
        key: fullKey,
        module,
        feature,
        name: meta?.name || fullKey,
        status: meta?.status || 'enabled',
        enabled: !!meta?.enabled,
        visible: !!meta?.visible,
        priority: meta?.priority ?? 0,
        scope: meta?.scope_type || 'GLOBAL',
        dependents: Array.isArray(meta?.dependents) ? meta.dependents : [],
        dependent_keys: Array.isArray(meta?.dependent_keys) ? meta.dependent_keys : [],
      };
    });

    const filtered = rows.filter((r) => {
      const matchesModule = moduleFilter === 'ALL' || r.module === moduleFilter;
      const q = query.trim().toLowerCase();
      const matchesQuery =
        !q || r.key.toLowerCase().includes(q) || (r.name || '').toLowerCase().includes(q);
      return matchesModule && matchesQuery;
    });

    filtered.sort(
      (a, b) =>
        b.priority - a.priority || a.module.localeCompare(b.module) || a.feature.localeCompare(b.feature),
    );

    return filtered;
  }, [features, query, moduleFilter]);

  const moduleOptions = useMemo(() => {
    const mods = new Set(Object.keys(features || {}).map((k) => k.split('.')[0]));
    return ['ALL', ...Array.from(mods).sort()];
  }, [features]);

  const confirmDisableIfNeeded = (record, nextEnabled) => {
    if (nextEnabled) return Promise.resolve(true);
    const dependents = record.dependents || [];
    if (!dependents.length) return Promise.resolve(true);
    return new Promise((resolve) => {
      Modal.confirm({
        title: 'Warning: Module Dependencies',
        content: (
          <div>
            <p>
              Disabling <strong>{record.name}</strong> will impact the following features/modules:
            </p>
            <ul style={{ paddingLeft: 18 }}>
              {dependents.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
            <p>Are you sure you want to proceed?</p>
          </div>
        ),
        okText: 'Confirm Disable',
        okButtonProps: { danger: true },
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      });
    });
  };

  const onToggle = async (record, checked) => {
    const proceed = await confirmDisableIfNeeded(record, checked);
    if (!proceed) {
      // Refresh to ensure UI remains consistent
      refreshFeatures();
      return;
    }
    try {
      await toggleFeature(record.module, record.feature, checked);
    } catch (e) {
      // FeatureContext logs errors; keep UI responsive
    }
  };

  const columns = [
    {
      title: 'Module',
      dataIndex: 'module',
      key: 'module',
      width: 140,
      render: (value) => <Text strong>{value}</Text>,
      filters: moduleOptions.filter((v) => v !== 'ALL').map((m) => ({ text: m, value: m })),
      onFilter: (val, record) => record.module === val,
    },
    {
      title: 'Feature',
      dataIndex: 'feature',
      key: 'feature',
      width: 220,
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text>{value}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.name}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 160,
      render: (value, record) => (
        <Space size={6}>
          <Tag color={record.enabled ? 'green' : 'red'}>
            {record.enabled ? 'Enabled' : 'Disabled'}
          </Tag>
          {value && value !== 'enabled' ? (
            <Tag color={value === 'beta' ? 'blue' : value === 'coming_soon' ? 'orange' : 'default'}>
              {String(value).replace('_', ' ')}
            </Tag>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Scope',
      dataIndex: 'scope',
      key: 'scope',
      width: 120,
      render: (value) => <Tag>{value}</Tag>,
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      sorter: (a, b) => a.priority - b.priority,
      defaultSortOrder: 'descend',
    },
    {
      title: 'Toggle',
      key: 'toggle',
      width: 140,
      render: (_, record) => (
        <Tooltip
          title={
            record.dependents?.length
              ? `Dependents: ${record.dependents.join(', ')}`
              : `Toggle ${record.key}`
          }
        >
          <Switch checked={record.enabled} onChange={(checked) => onToggle(record, checked)} loading={loading} />
        </Tooltip>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      <Space wrap>
        <Input
          placeholder="Search feature or name"
          allowClear
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: 260 }}
        />
        <Select
          value={moduleFilter}
          style={{ width: 200 }}
          onChange={setModuleFilter}
          options={moduleOptions.map((v) => ({ value: v, label: v }))}
        />
        <Button icon={<ReloadOutlined />} onClick={() => refreshFeatures()} disabled={loading}>
          Refresh
        </Button>
      </Space>
      <Table
        size="small"
        bordered
        rowKey="key"
        loading={loading}
        dataSource={data}
        columns={columns}
        pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100] }}
      />
    </Space>
  );
};

export default FeatureToggleManager;

