import React, { useMemo } from 'react';
import { ArrowDownOutlined, ArrowUpOutlined, DeleteOutlined } from '@ant-design/icons';
import { Button, Card, Empty, Input, List, Select, Space, Tag, Tooltip, Typography } from 'antd';

const { Title, Text } = Typography;

const FieldConfigurator = ({ availableFields = [], value = [], onChange }) => {
  const selectionOptions = useMemo(
    () =>
      availableFields.map((field) => ({
        label: field.label || field.name,
        value: field.name,
      })),
    [availableFields],
  );

  const selectedFieldKeys = value.map((field) => field.field);

  const handleSelectionChange = (selectedKeys) => {
    const fieldsByKey = new Map(value.map((field) => [field.field, field]));
    const nextFields = selectedKeys.map((key) => {
      const existing = fieldsByKey.get(key);
      if (existing) return existing;
      const fallback = availableFields.find((field) => field.name === key) || { name: key };
      return {
        id: key,
        key,
        field: key,
        label: fallback.label || key,
        alias: key,
        source: { path: key },
      };
    });
    onChange?.(nextFields);
  };

  const handleAliasChange = (fieldKey, alias) => {
    onChange?.(
      value.map((field) =>
        field.field === fieldKey
          ? {
              ...field,
              alias,
            }
          : field,
      ),
    );
  };

  const handleRemove = (fieldKey) => {
    onChange?.(value.filter((field) => field.field !== fieldKey));
  };

  const handleReorder = (fieldKey, direction) => {
    const index = value.findIndex((field) => field.field === fieldKey);
    if (index < 0) return;
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= value.length) return;
    const next = [...value];
    const [removed] = next.splice(index, 1);
    next.splice(targetIndex, 0, removed);
    onChange?.(next);
  };

  return (
    <Card
      title={
        <Title level={5} style={{ margin: 0 }}>
          2. Select Fields
        </Title>
      }
      bordered={false}
    >
      <Select
        mode="multiple"
        value={selectedFieldKeys}
        onChange={handleSelectionChange}
        placeholder="Add fields to include in the report"
        options={selectionOptions}
        style={{ width: '100%' }}
      />

      <div style={{ marginTop: 16 }}>
        {value.length === 0 ? (
          <Empty description="Choose fields to start designing your report." />
        ) : (
          <List
            dataSource={value}
            renderItem={(field, index) => (
              <List.Item
                key={field.field}
                actions={[
                  <Tooltip title="Move up" key="up">
                    <Button
                      size="small"
                      type="text"
                      icon={<ArrowUpOutlined />}
                      disabled={index === 0}
                      onClick={() => handleReorder(field.field, 'up')}
                    />
                  </Tooltip>,
                  <Tooltip title="Move down" key="down">
                    <Button
                      size="small"
                      type="text"
                      icon={<ArrowDownOutlined />}
                      disabled={index === value.length - 1}
                      onClick={() => handleReorder(field.field, 'down')}
                    />
                  </Tooltip>,
                  <Tooltip title="Remove field" key="remove">
                    <Button
                      size="small"
                      danger
                      type="text"
                      icon={<DeleteOutlined />}
                      onClick={() => handleRemove(field.field)}
                    />
                  </Tooltip>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{field.label}</Text>
                      <Tag>{field.field}</Tag>
                    </Space>
                  }
                  description={
                    <Input
                      size="small"
                      value={field.alias}
                      onChange={(event) => handleAliasChange(field.field, event.target.value)}
                      placeholder="Column alias"
                    />
                  }
                />
              </List.Item>
            )}
          />
        )}
      </div>
    </Card>
  );
};

export default FieldConfigurator;
