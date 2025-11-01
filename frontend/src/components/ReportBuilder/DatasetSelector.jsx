import React, { useMemo, useState } from 'react';
import { Card, Input, List, Skeleton, Tag, Typography } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';

const { Paragraph, Text, Title } = Typography;

const DatasetSelector = ({ datasets = [], value, onSelect, loading }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredDatasets = useMemo(() => {
    if (!searchTerm) return datasets;
    const term = searchTerm.toLowerCase();
    return datasets.filter((dataset) => dataset.label?.toLowerCase().includes(term));
  }, [datasets, searchTerm]);

  return (
    <Card
      title={
        <SpaceWithIcon icon={<DatabaseOutlined />}>
          <Title level={5} style={{ margin: 0 }}>
            1. Choose Data Source
          </Title>
        </SpaceWithIcon>
      }
      extra={
        <Input.Search
          placeholder="Search datasets"
          allowClear
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          style={{ width: 240 }}
        />
      }
      bordered={false}
    >
      <Skeleton loading={loading} active>
        <List
          grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3 }}
          dataSource={filteredDatasets}
          renderItem={(dataset) => {
            const isSelected = value?.key === dataset.key || value?.slug === dataset.slug;
            return (
              <List.Item key={dataset.key || dataset.slug}>
                <Card
                  hoverable
                  onClick={() => onSelect?.(dataset)}
                  style={{
                    borderColor: isSelected ? '#1890ff' : undefined,
                    boxShadow: isSelected ? '0 0 0 2px rgba(24, 144, 255, 0.25)' : undefined,
                    height: '100%',
                  }}
                >
                  <Title level={5} style={{ marginBottom: 8 }}>
                    {dataset.label}
                  </Title>
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                    {dataset.description || 'Metadata-driven dataset'}
                  </Paragraph>
                  <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    <Tag color="blue">{dataset.type}</Tag>
                    {dataset.scope_type && <Tag>{dataset.scope_type}</Tag>}
                  </div>
                  <Text type="secondary">{dataset.fields?.length || 0} fields</Text>
                </Card>
              </List.Item>
            );
          }}
        />
      </Skeleton>
    </Card>
  );
};

const SpaceWithIcon = ({ icon, children }) => (
  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
    {icon}
    {children}
  </div>
);

export default DatasetSelector;
