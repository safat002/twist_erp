import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  List,
  Modal,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
} from 'antd';
import api from '../../services/api';
import { trackMetadataInterest } from '../../services/ai';

const { Title, Text } = Typography;

const fieldTypes = [
  { label: 'Text', value: 'text' },
  { label: 'Number', value: 'number' },
  { label: 'Date', value: 'date' },
  { label: 'Boolean', value: 'boolean' },
  { label: 'Select', value: 'select' },
];

const SchemaDesigner = () => {
  const [definitions, setDefinitions] = useState([]);
  const [selectedDefinition, setSelectedDefinition] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fieldModalVisible, setFieldModalVisible] = useState(false);
  const [fieldForm] = Form.useForm();
  const [error, setError] = useState(null);

  const loadDefinitions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/v1/metadata/definitions/', {
        params: { kind: 'FORM', status: 'active' },
      });
      setDefinitions(response.data || []);
      return response.data || [];
    } catch (err) {
      setError(err?.message || 'Failed to load metadata definitions.');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDefinitions();
  }, [loadDefinitions]);

  const openFieldModal = (definition) => {
    setSelectedDefinition(definition);
    fieldForm.resetFields();
    setFieldModalVisible(true);
    if (definition?.key) {
      trackMetadataInterest({
        kind: 'field',
        entity: definition.key,
        definition_key: definition.key,
      }).catch(() => {});
    }
  };

  const handleAddField = async () => {
    try {
      const values = await fieldForm.validateFields();
      const payload = {
        ...values,
        required: values.required || false,
        options: values.options ? values.options.split(',').map((item) => item.trim()) : [],
        metadata: {},
        publish: values.publish || false,
      };

      const { data: newDefinition } = await api.post(
        `/api/v1/metadata/definitions/${selectedDefinition.id}/fields/`,
        payload,
      );
      setFieldModalVisible(false);
      const refreshed = await loadDefinitions();
      if (newDefinition) {
        setSelectedDefinition(newDefinition);
      } else if (refreshed) {
        const match = refreshed.find((item) => item.id === selectedDefinition.id);
        setSelectedDefinition(match || selectedDefinition);
      }
    } catch (err) {
      if (err?.response?.data?.detail) {
        Modal.error({ title: 'Validation error', content: err.response.data.detail });
      }
    }
  };

  const fieldsForDefinition = useMemo(() => {
    if (!selectedDefinition) {
      return [];
    }
    return selectedDefinition.definition?.fields || [];
  }, [selectedDefinition]);

  return (
    <div>
      <Title level={2}>Schema Designer</Title>
      <Text type="secondary">
        Extend metadata-driven entities with additional fields. Published changes become part of the active layer.
      </Text>
      {error ? (
        <Alert type="error" showIcon message={error} style={{ marginTop: 16 }} />
      ) : null}
      <List
        style={{ marginTop: 24 }}
        loading={loading}
        grid={{ gutter: 16, column: 2 }}
        dataSource={definitions}
        renderItem={(item) => (
          <List.Item key={item.id}>
            <Card
              title={item.key}
              extra={
                <Button type="link" onClick={() => openFieldModal(item)}>
                  Add Field
                </Button>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text type="secondary">Kind: {item.kind}</Text>
                <Text type="secondary">Layer: {item.layer}</Text>
                <Text type="secondary">Version: {item.version}</Text>
                <Text type="secondary">Scope: {item.scope_type}</Text>
                <div>
                  <Text strong>Fields</Text>
                  <div style={{ marginTop: 8 }}>
                    {(item.definition?.fields || []).map((field) => (
                      <Tag key={field.name} color={field.required ? 'red' : 'blue'}>
                        {field.label || field.name}
                      </Tag>
                    ))}
                    {!(item.definition?.fields || []).length ? (
                      <Text type="secondary"> No fields defined.</Text>
                    ) : null}
                  </div>
                </div>
              </Space>
            </Card>
          </List.Item>
        )}
      />

      <Modal
        title={selectedDefinition ? `Add field to ${selectedDefinition.key}` : 'Add field'}
        open={fieldModalVisible}
        onCancel={() => setFieldModalVisible(false)}
        onOk={handleAddField}
        okText="Add Field"
      >
        <Form layout="vertical" form={fieldForm}>
          <Form.Item
            label="Field name"
            name="name"
            rules={[
              { required: true, message: 'Provide a unique field identifier.' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: 'Use alpha-numeric characters and underscores.' },
            ]}
          >
            <Input placeholder="internal_name" />
          </Form.Item>
          <Form.Item
            label="Label"
            name="label"
            rules={[{ required: true, message: 'Provide a display label.' }]}
          >
            <Input placeholder="Display Label" />
          </Form.Item>
          <Form.Item label="Field type" name="type" rules={[{ required: true }]}> 
            <Select options={fieldTypes} placeholder="Select a field type" />
          </Form.Item>
          <Form.Item label="Required" name="required" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            label="Options (comma separated)"
            name="options"
            tooltip="Only used for select fields."
          >
            <Input placeholder="Option A, Option B, Option C" />
          </Form.Item>
          <Form.Item label="Publish immediately" name="publish" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        width={360}
        title={selectedDefinition ? selectedDefinition.key : 'Definition'}
        open={Boolean(selectedDefinition && !fieldModalVisible)}
        onClose={() => setSelectedDefinition(null)}
      >
        {selectedDefinition ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text strong>Fields</Text>
            {fieldsForDefinition.length ? (
              fieldsForDefinition.map((field) => (
                <Card key={field.name} size="small">
                  <Text strong>{field.label}</Text>
                  <br />
                  <Text type="secondary">Name: {field.name}</Text>
                  <br />
                  <Text type="secondary">Type: {field.type}</Text>
                  <br />
                  <Text type="secondary">Required: {field.required ? 'Yes' : 'No'}</Text>
                </Card>
              ))
            ) : (
              <Text type="secondary">No fields defined yet.</Text>
            )}
          </Space>
        ) : null}
      </Drawer>
    </div>
  );
};

export default SchemaDesigner;
