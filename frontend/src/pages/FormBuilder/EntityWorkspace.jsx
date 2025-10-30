import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import dayjs from 'dayjs';

import PageHeader from '../../components/Common/PageHeader';
import api from '../../services/api';

const { Text } = Typography;

const EntityWorkspace = () => {
  const { slug } = useParams();
  const [schema, setSchema] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalMode, setModalMode] = useState('create');
  const [currentRecord, setCurrentRecord] = useState(null);
  const [savingRecord, setSavingRecord] = useState(false);
  const [form] = Form.useForm();

  const loadSchema = async () => {
    const { data } = await api.get(`/api/v1/forms/entities/${slug}/`);
    setSchema(data);
  };

  const loadRecords = async () => {
    setRecordsLoading(true);
    try {
      const { data } = await api.get(`/api/v1/forms/entities/${slug}/records/`);
      const payload = Array.isArray(data) ? data : data?.results || [];
      setRecords(payload);
    } finally {
      setRecordsLoading(false);
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      setLoading(true);
      try {
        await loadSchema();
        await loadRecords();
      } catch (error) {
        console.error('Failed to load entity workspace', error);
        message.error('Unable to load entity workspace.');
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, [slug]);

  const fields = schema?.fields || [];

  const openCreate = () => {
    setModalMode('create');
    setCurrentRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  const openEdit = (record) => {
    setModalMode('edit');
    setCurrentRecord(record);
    form.setFieldsValue(mapRecordToForm(record, fields));
    setModalVisible(true);
  };

  const handleDelete = async (recordId) => {
    try {
      await api.delete(`/api/v1/forms/entities/${slug}/records/${recordId}/`);
      message.success('Record deleted.');
      loadRecords();
    } catch (error) {
      console.error('Failed to delete record', error);
      message.error('Unable to delete record.');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = preparePayload(values, fields);
      setSavingRecord(true);
      if (modalMode === 'edit' && currentRecord?.id) {
        await api.put(`/api/v1/forms/entities/${slug}/records/${currentRecord.id}/`, payload);
        message.success('Record updated.');
      } else {
        await api.post(`/api/v1/forms/entities/${slug}/records/`, payload);
        message.success('Record created.');
      }
      setModalVisible(false);
      loadRecords();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      console.error('Failed to save record', error);
      message.error('Unable to save record.');
    } finally {
      setSavingRecord(false);
    }
  };

  const columns = useMemo(() => buildColumns(fields, openEdit, handleDelete), [fields]);

  if (loading) {
    return (
      <div>
        <PageHeader title="Loading entity..." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={schema?.name || 'Generated Entity'}
        subtitle={schema?.description}
        description={schema?.api_path ? `API endpoint: ${schema.api_path}` : undefined}
        extra={
          <Button type="primary" onClick={openCreate}>
            New Record
          </Button>
        }
      />

      <Card>
        <Table
          rowKey="id"
          loading={recordsLoading}
          columns={columns}
          dataSource={records}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No records yet. Add your first entry.' }}
        />
      </Card>

      <Modal
        title={modalMode === 'edit' ? 'Edit Record' : 'New Record'}
        open={modalVisible}
        okText={modalMode === 'edit' ? 'Save Changes' : 'Create'}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmit}
        confirmLoading={savingRecord}
        destroyOnClose
        width={520}
      >
        <Form layout="vertical" form={form}>
          {fields.map((field) => (
            <Form.Item
              key={field.name}
              label={field.label || field.name}
              name={field.name}
              rules={
                field.required
                  ? [
                      {
                        required: true,
                        message: `${field.label || field.name} is required.`,
                      },
                    ]
                  : []
              }
              valuePropName={field.type === 'boolean' ? 'checked' : 'value'}
            >
              {renderInput(field)}
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </div>
  );
};

const buildColumns = (fields, onEdit, onDelete) => {
  const baseColumns = fields.map((field) => ({
    title: field.label || field.name,
    dataIndex: field.name,
    key: field.name,
    render: (value) => renderValue(field.type, value),
  }));

  baseColumns.push({
    title: 'Actions',
    key: 'actions',
    render: (_, record) => (
      <Space>
        <Button type="link" onClick={() => onEdit(record)}>
          Edit
        </Button>
        <Popconfirm title="Delete this record?" onConfirm={() => onDelete(record.id)}>
          <Button type="link" danger>
            Delete
          </Button>
        </Popconfirm>
      </Space>
    ),
  });

  return baseColumns;
};

const renderInput = (field) => {
  switch (field.type) {
    case 'text':
      return <Input.TextArea rows={3} />;
    case 'decimal':
      return <Input type="number" />;
    case 'date':
      return <DatePicker style={{ width: '100%' }} />;
    case 'boolean':
      return <Switch />;
    default:
      return <Input />;
  }
};

const mapRecordToForm = (record, fields) => {
  const payload = {};
  fields.forEach((field) => {
    let value = record[field.name];
    if (field.type === 'date' && value) {
      value = dayjs(value);
    }
    payload[field.name] = value;
  });
  return payload;
};

const preparePayload = (values, fields) => {
  const payload = { ...values };
  fields.forEach((field) => {
    if (field.type === 'date' && values[field.name]) {
      payload[field.name] = values[field.name].format('YYYY-MM-DD');
    }
  });
  return payload;
};

const renderValue = (fieldType, value) => {
  if (value === null || value === undefined || value === '') {
    return <Text type="secondary">—</Text>;
  }

  switch (fieldType) {
    case 'decimal':
      return Number(value).toLocaleString();
    case 'date':
      return dayjs(value).format('YYYY-MM-DD');
    case 'boolean':
      return value ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag>;
    default:
      return <Text>{value}</Text>;
  }
};

export default EntityWorkspace;
