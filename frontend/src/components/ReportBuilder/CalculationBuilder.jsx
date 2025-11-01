import React from 'react';
import { Button, Card, Input, Space, Tag, Typography } from 'antd';
import { FunctionOutlined, PlusOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

const CalculationBuilder = ({ fields = [], value = [], onChange }) => {
  const handleAdd = () => {
    const next = [
      ...value,
      {
        id: `calc_${Date.now()}`,
        label: 'Calculated Field',
        expression: '',
      },
    ];
    onChange?.(next);
  };

  const handleUpdate = (index, updates) => {
    const next = value.map((calculation, position) =>
      position === index ? { ...calculation, ...updates } : calculation,
    );
    onChange?.(next);
  };

  const handleRemove = (index) => {
    onChange?.(value.filter((_, position) => position !== index));
  };

  const fieldTokens = fields.map((field) => (
    <Tag key={field.alias || field.field} color="geekblue">
      {field.alias || field.field}
    </Tag>
  ));

  return (
    <Card
      title={
        <Space>
          <FunctionOutlined />
          <Title level={5} style={{ margin: 0 }}>
            5. Calculated Fields
          </Title>
        </Space>
      }
      extra={
        <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={handleAdd}>
          Add Calculation
        </Button>
      }
      bordered={false}
    >
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary">Reference columns by their alias (tokens below) in expressions.</Text>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>{fieldTokens}</div>
      </div>
      {value.length === 0 ? (
        <Text type="secondary">No calculated fields added.</Text>
      ) : (
        value.map((calc, index) => (
          <Card
            key={calc.id || index}
            size="small"
            style={{ marginBottom: 12 }}
            title={
              <Input
                size="small"
                value={calc.label}
                onChange={(event) => handleUpdate(index, { label: event.target.value })}
                placeholder="Calculated field label"
              />
            }
            extra={
              <Button danger size="small" type="link" onClick={() => handleRemove(index)}>
                Remove
              </Button>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input
                size="small"
                value={calc.id}
                onChange={(event) => handleUpdate(index, { id: event.target.value })}
                placeholder="Result key (used in exports)"
              />
              <TextArea
                rows={3}
                value={calc.expression}
                onChange={(event) => handleUpdate(index, { expression: event.target.value })}
                placeholder="Example: revenue - cost"
              />
            </Space>
          </Card>
        ))
      )}
    </Card>
  );
};

export default CalculationBuilder;
