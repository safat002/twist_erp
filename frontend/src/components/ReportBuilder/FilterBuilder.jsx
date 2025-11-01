import React from 'react';
import { Button, Card, Divider, Input, Select, Space, Typography } from 'antd';
import { FilterOutlined, PlusOutlined } from '@ant-design/icons';

const { Title } = Typography;

const operatorOptions = [
  { label: 'Equals', value: 'equals' },
  { label: 'Not Equals', value: 'not_equals' },
  { label: 'Contains', value: 'contains' },
  { label: 'Starts With', value: 'icontains' },
  { label: 'Greater Than', value: 'gt' },
  { label: 'Less Than', value: 'lt' },
  { label: 'Greater or Equal', value: 'gte' },
  { label: 'Less or Equal', value: 'lte' },
  { label: 'In (comma separated)', value: 'in' },
  { label: 'Is Null', value: 'is_null' },
];

const logicOptions = [
  { label: 'AND', value: 'AND' },
  { label: 'OR', value: 'OR' },
];

const FilterBuilder = ({ fields = [], value = [], onChange }) => {
  const fieldOptions = fields.map((field) => ({
    label: field.label || field.name,
    value: field.field || field.name,
  }));

  const handleAddFilter = () => {
    const nextFilters = [
      ...value,
      {
        id: `filter-${Date.now()}`,
        field: fieldOptions[0]?.value || null,
        operator: 'equals',
        value: '',
        logic: 'AND',
      },
    ];
    onChange?.(nextFilters);
  };

  const handleUpdateFilter = (index, updates) => {
    const nextFilters = value.map((filter, position) =>
      position === index ? { ...filter, ...updates } : filter,
    );
    onChange?.(nextFilters);
  };

  const handleRemoveFilter = (index) => {
    const nextFilters = value.filter((_, position) => position !== index);
    onChange?.(nextFilters);
  };

  return (
    <Card
      title={
        <Space>
          <FilterOutlined />
          <Title level={5} style={{ margin: 0 }}>
            3. Add Filters
          </Title>
        </Space>
      }
      extra={
        <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={handleAddFilter}>
          Add Filter
        </Button>
      }
      bordered={false}
    >
      {value.length === 0 ? (
        <Typography.Text type="secondary">No filters applied yet.</Typography.Text>
      ) : (
        value.map((filter, index) => (
          <React.Fragment key={filter.id || index}>
            {index > 0 && <Divider plain>{filter.logic || 'AND'}</Divider>}
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space wrap style={{ width: '100%' }}>
                <Select
                  style={{ minWidth: 160 }}
                  placeholder="Field"
                  options={fieldOptions}
                  value={filter.field}
                  onChange={(field) => handleUpdateFilter(index, { field })}
                />
                <Select
                  style={{ minWidth: 160 }}
                  placeholder="Operator"
                  options={operatorOptions}
                  value={filter.operator}
                  onChange={(operator) => handleUpdateFilter(index, { operator })}
                />
                {filter.operator !== 'is_null' ? (
                  <Input
                    style={{ minWidth: 200 }}
                    placeholder="Value"
                    value={filter.value}
                    onChange={(event) => handleUpdateFilter(index, { value: event.target.value })}
                  />
                ) : null}
                <Select
                  style={{ width: 100 }}
                  options={logicOptions}
                  value={filter.logic || 'AND'}
                  onChange={(logic) => handleUpdateFilter(index, { logic })}
                />
                <Button danger onClick={() => handleRemoveFilter(index)}>
                  Remove
                </Button>
              </Space>
            </Space>
          </React.Fragment>
        ))
      )}
    </Card>
  );
};

export default FilterBuilder;
