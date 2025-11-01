import React from 'react';
import { ArrowDownOutlined, ArrowUpOutlined, SortAscendingOutlined } from '@ant-design/icons';
import { Button, Card, Select, Space, Typography } from 'antd';

const { Title } = Typography;

const SortBuilder = ({ fields = [], value = [], onChange }) => {
  const fieldOptions = fields.map((field) => ({
    label: field.label || field.name,
    value: field.field || field.name,
  }));

  const handleAddSort = () => {
    if (!fieldOptions.length) return;
    const next = [
      ...value,
      {
        id: `sort-${Date.now()}`,
        field: fieldOptions[0].value,
        direction: 'asc',
      },
    ];
    onChange?.(next);
  };

  const handleUpdate = (index, updates) => {
    const next = value.map((sort, position) =>
      position === index ? { ...sort, ...updates } : sort,
    );
    onChange?.(next);
  };

  const handleRemove = (index) => {
    onChange?.(value.filter((_, position) => position !== index));
  };

  return (
    <Card
      title={
        <Space>
          <SortAscendingOutlined />
          <Title level={5} style={{ margin: 0 }}>
            4. Sorting
          </Title>
        </Space>
      }
      extra={
        <Button type="dashed" size="small" onClick={handleAddSort}>
          Add Sort
        </Button>
      }
      bordered={false}
    >
      {value.length === 0 ? (
        <Typography.Text type="secondary">No sorting applied.</Typography.Text>
      ) : (
        value.map((sort, index) => (
          <Space key={sort.id || index} wrap style={{ width: '100%', marginBottom: 12 }}>
            <Select
              style={{ minWidth: 180 }}
              options={fieldOptions}
              value={sort.field}
              onChange={(field) => handleUpdate(index, { field })}
            />
            <Select
              style={{ width: 120 }}
              value={sort.direction}
              onChange={(direction) => handleUpdate(index, { direction })}
              options={[
                { label: <DirectionLabel icon={<ArrowUpOutlined />} text="Ascending" />, value: 'asc' },
                { label: <DirectionLabel icon={<ArrowDownOutlined />} text="Descending" />, value: 'desc' },
              ]}
            />
            <Button danger type="link" onClick={() => handleRemove(index)}>
              Remove
            </Button>
          </Space>
        ))
      )}
    </Card>
  );
};

const DirectionLabel = ({ icon, text }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
    {icon}
    {text}
  </span>
);

export default SortBuilder;
