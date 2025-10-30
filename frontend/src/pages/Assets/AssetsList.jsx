import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Input,
  Space,
  Table,
  Tag,
  Typography,
  Select,
  Tooltip,
} from 'antd';
import { ReloadOutlined, FileAddOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import PageHeader from '../../components/Common/PageHeader';
import api from '../../services/api';

const { Text } = Typography;

const STATUS_BADGES = {
  ACTIVE: 'green',
  MAINTENANCE: 'orange',
  RETIRED: 'default',
};

const AssetRegister = () => {
  const [loading, setLoading] = useState(false);
  const [assets, setAssets] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    loadAssets();
  }, [statusFilter]);

  useEffect(() => {
    if (!searchQuery) {
      setFiltered(assets);
      return;
    }
    const lowered = searchQuery.toLowerCase();
    setFiltered(
      assets.filter(
        (asset) =>
          asset.name?.toLowerCase().includes(lowered) ||
          asset.code?.toLowerCase().includes(lowered) ||
          asset.category?.toLowerCase().includes(lowered) ||
          asset.location?.toLowerCase().includes(lowered),
      ),
    );
  }, [searchQuery, assets]);

  const loadAssets = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      const { data } = await api.get('/api/v1/assets/register/', { params });
      setAssets(Array.isArray(data) ? data : []);
      setFiltered(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load assets register', error);
      setAssets([]);
      setFiltered([]);
    } finally {
      setLoading(false);
    }
  };

  const columns = useMemo(
    () => [
      {
        title: 'Asset Tag',
        dataIndex: 'code',
        key: 'code',
        render: (value) => <Text strong>{value}</Text>,
      },
      {
        title: 'Asset Name',
        dataIndex: 'name',
        key: 'name',
        render: (value, record) => (
          <Space direction="vertical" size={0}>
            <Text>{value}</Text>
            <Text type="secondary">
              {record.manufacturer || '—'} {record.model_number || ''}
            </Text>
          </Space>
        ),
      },
      {
        title: 'Category',
        dataIndex: 'category',
        key: 'category',
        render: (value) => value || 'Uncategorised',
      },
      {
        title: 'Location',
        dataIndex: 'location',
        key: 'location',
        render: (value) => value || '—',
      },
      {
        title: 'Acquired',
        dataIndex: 'acquisition_date',
        key: 'acquisition_date',
        render: (value) => (value ? dayjs(value).format('DD MMM YYYY') : '—'),
      },
      {
        title: 'Cost',
        dataIndex: 'cost',
        key: 'cost',
        align: 'right',
        render: (value) =>
          typeof value === 'number' || typeof value === 'string'
            ? Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })
            : '0.00',
      },
      {
        title: 'Book Value',
        dataIndex: 'book_value',
        key: 'book_value',
        align: 'right',
        render: (value) =>
          Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }),
      },
      {
        title: 'Depreciation to Date',
        dataIndex: 'depreciation_to_date',
        key: 'depreciation_to_date',
        align: 'right',
        render: (value) =>
          Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }),
      },
      {
        title: 'Months in Service',
        dataIndex: 'months_in_service',
        key: 'months_in_service',
        align: 'center',
      },
      {
        title: 'Next Maintenance',
        dataIndex: 'next_maintenance',
        key: 'next_maintenance',
        render: (value) => {
          if (!value) return <Tag color="default">Not scheduled</Tag>;
          const due = value.due_date ? dayjs(value.due_date).format('DD MMM YYYY') : 'TBC';
          return (
            <Space size={4}>
              <Tag color="blue">{value.title}</Tag>
              <Text type="secondary">{due}</Text>
            </Space>
          );
        },
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (value) => (
          <Tag color={STATUS_BADGES[value] || 'default'}>{value?.replace('_', ' ')}</Tag>
        ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader
        title="Asset Register"
        subtitle="Track capital assets, book values, and depreciation insight"
        extra={
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'ALL', label: 'All statuses' },
                { value: 'ACTIVE', label: 'Active' },
                { value: 'MAINTENANCE', label: 'In maintenance' },
                { value: 'RETIRED', label: 'Retired' },
              ]}
              style={{ width: 180 }}
            />
            <Input.Search
              allowClear
              placeholder="Search assets..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              style={{ width: 240 }}
            />
            <Tooltip title="Refresh register">
              <Button icon={<ReloadOutlined />} onClick={loadAssets} loading={loading} />
            </Tooltip>
            <Button type="primary" icon={<FileAddOutlined />}>
              New Asset
            </Button>
          </Space>
        }
      />

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={filtered}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default AssetRegister;
