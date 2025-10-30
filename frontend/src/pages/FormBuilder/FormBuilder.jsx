import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Input,
  Select,
  Checkbox,
  Form,
  Typography,
  message,
  Tabs,
  Divider,
  List,
  Switch,
  Tag,
} from 'antd';
import {
  PlusOutlined,
  SaveOutlined,
  EyeOutlined,
  FormOutlined,
  FieldNumberOutlined,
  CalendarOutlined,
  DownOutlined,
  CheckSquareOutlined,
  MailOutlined,
  PhoneOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useCompany } from '../../contexts/CompanyContext';

const { Title, Text } = Typography;
const { Option } = Select;

const paletteFields = [
  { type: 'text', label: 'Text Input', icon: <FormOutlined /> },
  { type: 'textarea', label: 'Paragraph', icon: <FormOutlined /> },
  { type: 'number', label: 'Number', icon: <FieldNumberOutlined /> },
  { type: 'date', label: 'Date Picker', icon: <CalendarOutlined /> },
  { type: 'select', label: 'Dropdown', icon: <DownOutlined /> },
  { type: 'checkbox', label: 'Checkbox', icon: <CheckSquareOutlined /> },
  { type: 'email', label: 'Email', icon: <MailOutlined /> },
  { type: 'phone', label: 'Phone', icon: <PhoneOutlined /> },
];

const fallbackTemplates = [
  {
    id: 'template-1',
    name: 'Employee Onboarding',
    description: 'Collect personal, banking, and role details for new hires.',
    fields: [
      { id: 'f1', type: 'text', label: 'Full Name', required: true, placeholder: 'Enter full name' },
      { id: 'f2', type: 'email', label: 'Work Email', required: true, placeholder: 'name@example.com' },
      { id: 'f3', type: 'select', label: 'Department', required: true, options: ['Production', 'Sales', 'Finance'] },
      { id: 'f4', type: 'date', label: 'Start Date', required: true },
    ],
  },
  {
    id: 'template-2',
    name: 'Vendor Registration',
    description: 'Capture supplier credentials, bank details, and compliance docs.',
    fields: [
      { id: 'f5', type: 'text', label: 'Vendor Name', required: true },
      { id: 'f6', type: 'phone', label: 'Contact Number', required: true },
      { id: 'f7', type: 'email', label: 'Primary Email', required: false },
      { id: 'f8', type: 'textarea', label: 'Service Description', required: false, placeholder: 'Products / services offered' },
    ],
  },
];

const defaultFieldProps = {
  placeholder: '',
  helperText: '',
  required: false,
  options: [],
};

const FormBuilder = () => {
  const { currentCompany } = useCompany();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState(fallbackTemplates);
  const [formName, setFormName] = useState('Untitled Form');
  const [formDescription, setFormDescription] = useState('');
  const [formFields, setFormFields] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [scopeType, setScopeType] = useState('COMPANY');
  const [publishNow, setPublishNow] = useState(true);
  const [generateModule, setGenerateModule] = useState(true);
  const [scaffoldResult, setScaffoldResult] = useState(null);
  const [latestMetadata, setLatestMetadata] = useState(null);

  const selectedField = useMemo(
    () => formFields.find((field) => field.id === selectedFieldId) || null,
    [formFields, selectedFieldId],
  );

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
          setTemplates(fallbackTemplates);
          return;
        }
        const response = await api.get('/api/v1/forms/templates/');
        const payload = response.data?.results || response.data || [];
        if (Array.isArray(payload) && payload.length) {
          setTemplates(payload);
        } else {
          setTemplates(fallbackTemplates);
        }
      } catch (error) {
        console.warn('Form templates fallback data used:', error?.message);
        setTemplates(fallbackTemplates);
      }
    };

    loadTemplates();
  }, [currentCompany]);

  const handleDragEnd = (result) => {
    const { destination, source } = result;
    if (!destination) return;

    if (source.droppableId === 'palette' && destination.droppableId === 'canvas') {
      const paletteField = paletteFields[source.index];
      const newField = {
        id: `field-${Date.now()}`,
        ...defaultFieldProps,
        type: paletteField.type,
        label: paletteField.label,
        icon: paletteField.icon,
        options: paletteField.type === 'select' ? ['Option 1', 'Option 2'] : [],
      };
      const updatedFields = [...formFields];
      updatedFields.splice(destination.index, 0, newField);
      setFormFields(updatedFields);
      setSelectedFieldId(newField.id);
      return;
    }

    if (source.droppableId === 'canvas' && destination.droppableId === 'canvas') {
      const updatedFields = Array.from(formFields);
      const [removed] = updatedFields.splice(source.index, 1);
      updatedFields.splice(destination.index, 0, removed);
      setFormFields(updatedFields);
    }
  };

  const handleTemplateApply = (template) => {
    setFormName(template.name);
    setFormDescription(template.description || '');
    setFormFields(template.fields.map((field) => ({ ...defaultFieldProps, ...field })));
    setSelectedFieldId(null);
  };

  const updateField = (fieldId, updates) => {
    setFormFields((prev) =>
      prev.map((field) => (field.id === fieldId ? { ...field, ...updates } : field)),
    );
  };

  const handleDeleteField = (fieldId) => {
    setFormFields((prev) => prev.filter((field) => field.id !== fieldId));
    if (selectedFieldId === fieldId) {
      setSelectedFieldId(null);
    }
  };

  const handleSave = async () => {
    if (!formName.trim()) {
      message.error('Please give your form a name.');
      return;
    }
    if (!formFields.length) {
      message.error('Add at least one field before saving.');
      return;
    }
    const payload = {
      name: formName,
      description: formDescription,
      schema: formFields,
      generate_scaffold: generateModule,
      scope_type: scopeType,
      layer: "COMPANY_OVERRIDE",
      publish: publishNow,
    };

    setSaving(true);
    try {
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        message.info('Demo company detected. Form saved locally.');
        setSaving(false);
        return;
      }
      const { data } = await api.post('/api/v1/forms/templates/', payload);
      if (data?.entity) {
        setScaffoldResult(data.entity);
        message.success('Form saved and module scaffolded.');
      } else {
        setScaffoldResult(null);
        message.success('Form saved successfully.');
      }
      setLatestMetadata(data.metadata || null);
      setScopeType(data.scope_type || 'COMPANY');
      setPublishNow((data.status || 'active') !== 'draft');
      setTemplates((prev) => {
        if (!Array.isArray(prev)) return prev;
        return [data, ...prev];
      });
    } catch (error) {
      console.warn('Failed to save form, using demo mode:', error?.message);
      setScaffoldResult(null);
      setLatestMetadata(null);
      const detail = error?.response?.data?.detail || 'Unable to save form right now.';
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  const renderFieldInput = (field) => {
    switch (field.type) {
      case 'textarea':
        return <Input.TextArea placeholder={field.placeholder} rows={3} />;
      case 'number':
        return <Input type="number" placeholder={field.placeholder} />;
      case 'date':
        return <Input placeholder="Date selection placeholder" />;
      case 'select':
        return (
          <Select placeholder={field.placeholder || 'Select option'}>
            {(field.options || []).map((option, idx) => (
              <Option key={idx} value={option}>
                {option}
              </Option>
            ))}
          </Select>
        );
      case 'checkbox':
        return <Checkbox>{field.placeholder || 'Checkbox label'}</Checkbox>;
      default:
        return <Input placeholder={field.placeholder} />;
    }
  };

  const previewForm = (
    <Form layout="vertical">
      {formFields.map((field) => (
        <Form.Item
          key={field.id}
          label={
            <Space>
              {field.label}
              {field.required && <span style={{ color: 'red' }}>*</span>}
            </Space>
          }
        >
          {renderFieldInput(field)}
          {field.helperText ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {field.helperText}
            </Text>
          ) : null}
        </Form.Item>
      ))}
    </Form>
  );

  return (
    <div>
      <Space align="center" size="small" style={{ marginBottom: 8 }}>
        <Title level={2} style={{ margin: 0 }}>
          No-Code Form Builder
        </Title>
        <Tag color="purple">Scaffolder v1</Tag>
      </Space>
      <Text type="secondary">
        Drag-and-drop fields, adjust properties, and instantly preview forms powered by Twist ERP’s
        schema engine.
      </Text>

      <Card
        style={{ marginTop: 16 }}
        title={
          <Space align="baseline">
            <Input
              value={formName}
              onChange={(event) => setFormName(event.target.value)}
              style={{ width: 260 }}
              placeholder="Form name"
            />
            <Input
              value={formDescription}
              onChange={(event) => setFormDescription(event.target.value)}
              style={{ width: 320 }}
              placeholder="Optional description"
            />
          </Space>
        }
        extra={
          <Space size="large" align="center">
            <Space size="small">
              <Text type="secondary">Scope</Text>
              <Select
                size="small"
                value={scopeType}
                onChange={setScopeType}
                style={{ width: 160 }}
                options={[
                  { label: 'Company', value: 'COMPANY' },
                  { label: 'Company Group', value: 'GROUP' },
                  { label: 'Global', value: 'GLOBAL' },
                ]}
              />
            </Space>
            <Space size="small">
              <Switch checked={publishNow} onChange={setPublishNow} />
              <Text type="secondary">{publishNow ? 'Publish now' : 'Save as draft'}</Text>
            </Space>
            <Space size="small">
              <Switch checked={generateModule} onChange={(checked) => setGenerateModule(checked)} />
              <Text type="secondary">Generate backend module</Text>
            </Space>
            <Button icon={<EyeOutlined />}>Preview</Button>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
              Save Schema
            </Button>
          </Space>
        }
      >
        <DragDropContext onDragEnd={handleDragEnd}>
          <Row gutter={16}>
            <Col xs={24} md={7} xl={6}>
              <Card title="Field Palette" size="small" bodyStyle={{ padding: 12 }}>
                <Droppable droppableId="palette" isDropDisabled>
                  {(provided) => (
                    <div ref={provided.innerRef} {...provided.droppableProps}>
                      {paletteFields.map((field, index) => (
                        <Draggable key={field.type} draggableId={field.type} index={index}>
                          {(dragProvided, snapshot) => (
                            <Card
                              size="small"
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              style={{
                                marginBottom: 8,
                                background: snapshot.isDragging ? '#e6f7ff' : '#fff',
                                border: '1px dashed #91d5ff',
                                cursor: 'grab',
                                ...dragProvided.draggableProps.style,
                              }}
                            >
                              <Space>
                                {field.icon}
                                <span>{field.label}</span>
                              </Space>
                            </Card>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </Card>
              <Card
                title="Starter Templates"
                size="small"
                style={{ marginTop: 16 }}
                bodyStyle={{ maxHeight: 240, overflow: 'auto', paddingRight: 4 }}
              >
                <List
                  dataSource={templates}
                  renderItem={(template) => (
                    <List.Item
                      key={template.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleTemplateApply(template)}
                    >
                      <Space direction="vertical" size={0}>
                        <Text strong>{template.name}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {template.description}
                        </Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>

            <Col xs={24} md={10} xl={12}>
              <Card
                title="Canvas"
                size="small"
                bodyStyle={{ minHeight: 520, padding: 0, background: '#fafafa' }}
              >
                <Droppable droppableId="canvas">
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      style={{
                        minHeight: 520,
                        padding: 16,
                        background: snapshot.isDraggingOver ? '#e6f7ff' : '#fafafa',
                      }}
                    >
                      {formFields.length === 0 && (
                        <div style={{ textAlign: 'center', color: '#a0a0a0', marginTop: 120 }}>
                          Drag blocks from the palette to start building
                        </div>
                      )}
                      {formFields.map((field, index) => (
                        <Draggable key={field.id} draggableId={field.id} index={index}>
                          {(dragProvided, dragSnapshot) => (
                            <Card
                              size="small"
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              style={{
                                marginBottom: 12,
                                border:
                                  selectedFieldId === field.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                                boxShadow: dragSnapshot.isDragging ? '0 8px 16px rgba(0,0,0,0.08)' : 'none',
                                cursor: 'pointer',
                                ...dragProvided.draggableProps.style,
                              }}
                              onClick={() => setSelectedFieldId(field.id)}
                            >
                              <Space align="baseline" style={{ justifyContent: 'space-between', width: '100%' }}>
                                <Space>
                                  {field.icon}
                                  <Text strong>{field.label}</Text>
                                  {field.required && <span style={{ color: 'red' }}>*</span>}
                                </Space>
                                <Button
                                  type="text"
                                  size="small"
                                  danger
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    handleDeleteField(field.id);
                                  }}
                                >
                                  Delete
                                </Button>
                              </Space>
                              {field.placeholder ? (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  Placeholder: {field.placeholder}
                                </Text>
                              ) : null}
                            </Card>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </Card>
            </Col>

            <Col xs={24} md={7} xl={6}>
              <Tabs
                defaultActiveKey="properties"
                items={[
                  {
                    key: 'properties',
                    label: 'Field Properties',
                    children: selectedField ? (
                      <>
                        <Form
                          layout="vertical"
                          initialValues={selectedField}
                          onValuesChange={(changed, all) => updateField(selectedField.id, all)}
                        >
                          <Form.Item name="label" label="Label">
                            <Input placeholder="Field label" />
                          </Form.Item>
                          <Form.Item name="placeholder" label="Placeholder">
                            <Input placeholder="Optional hint" />
                          </Form.Item>
                          <Form.Item name="helperText" label="Helper Text">
                            <Input placeholder="Shown under the field" />
                          </Form.Item>
                          <Form.Item name="required" valuePropName="checked">
                            <Checkbox>Required</Checkbox>
                          </Form.Item>
                          {selectedField.type === 'select' ? (
                            <Form.Item name="options" label="Options">
                              <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                placeholder="Press enter to add options"
                              />
                            </Form.Item>
                          ) : null}
                        </Form>
                        <Divider />
                        <Text type="secondary">
                          Configure validation, default values, and automation triggers using the Twist ERP rule
                          engine.
                        </Text>
                      </>
                    ) : (
                      <Text type="secondary">Select a field to edit its properties.</Text>
                    ),
                  },
                  {
                    key: 'preview',
                    label: 'Preview',
                    children: <div style={{ maxHeight: 420, overflow: 'auto' }}>{previewForm}</div>,
                  },
                  {
                    key: 'meta',
                    label: 'Insights',
                    children: (
                      <List
                        dataSource={[
                          {
                            id: 'insight-1',
                            title: 'Automate follow-up emails',
                            detail: 'Use workflow studio when form is submitted to notify responsible teams.',
                          },
                          {
                            id: 'insight-2',
                            title: 'Expose via portal',
                            detail: 'Expose this form in customer/vendor portals with role-based permissions.',
                          },
                        ]}
                        renderItem={(item) => (
                          <List.Item key={item.id}>
                            <Space>
                              <ThunderboltOutlined style={{ color: '#722ed1' }} />
                              <Space direction="vertical" size={0}>
                                <Text strong>{item.title}</Text>
                                <Text type="secondary">{item.detail}</Text>
                              </Space>
                            </Space>
                          </List.Item>
                        )}
                      />
                    ),
                  },
                ]}
              />
            </Col>
          </Row>
        </DragDropContext>
      </Card>
      {latestMetadata ? (
        <Card style={{ marginTop: 16 }} title="Metadata version">
          <Space direction="vertical">
            <Text strong>{latestMetadata.key}</Text>
            <Text type="secondary">Version {latestMetadata.version} - {latestMetadata.status}</Text>
            <Text type="secondary">Scope: {latestMetadata.scope_type}</Text>
          </Space>
        </Card>
      ) : null}
      {scaffoldResult ? (
        <Card
          style={{ marginTop: 16 }}
          title="Module scaffolded"
          extra={
            <Button type="link" onClick={() => navigate(`/forms/entities/${scaffoldResult.slug}`)}>
              Open module
            </Button>
          }
        >
          <Space direction="vertical">
            <Text strong>{scaffoldResult.name}</Text>
            <Text type="secondary">API endpoint: {scaffoldResult.api_path}</Text>
            <Text type="secondary">
              Fields:{' '}
              {(scaffoldResult.fields || [])
                .map((field) => field.label || field.name)
                .join(', ')}
            </Text>
          </Space>
        </Card>
      ) : null}
    </div>
  );
};

export default FormBuilder;
