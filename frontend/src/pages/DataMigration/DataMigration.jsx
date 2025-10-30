import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Steps,
  Table,
  Space,
  Button,
  Typography,
  Tag,
  List,
  Upload,
  message,
  Form,
  Select,
  Input,
  Modal,
  Descriptions,
  Empty,
  Spin,
  Divider,
  Switch,
} from 'antd';
import {
  UploadOutlined,
  ThunderboltOutlined,
  FileSearchOutlined,
  CheckCircleOutlined,
  AlertOutlined,
  CloudSyncOutlined,
  FileOutlined,
  ReloadOutlined,
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useCompany } from '../../contexts/CompanyContext';
import {
  listMigrationJobs,
  getMigrationJob,
  createMigrationJob,
  uploadMigrationFile,
  profileMigrationJob,
  stageMigrationJob,
  validateMigrationJob,
  submitMigrationJob,
  approveMigrationJob,
  commitMigrationJob,
  rollbackMigrationJob,
  updateMapping,
} from '../../services/dataMigration';

const { Title, Text } = Typography;

const STEP_ITEMS = [
  { title: 'Upload', icon: <UploadOutlined /> },
  { title: 'Map Fields', icon: <FileSearchOutlined /> },
  { title: 'Validate', icon: <AlertOutlined /> },
  { title: 'Approval', icon: <CheckCircleOutlined /> },
  { title: 'Commit', icon: <CloudSyncOutlined /> },
];

const STATUS_STEP_MAP = {
  uploaded: 0,
  detected: 1,
  mapped: 1,
  validated: 2,
  awaiting_approval: 3,
  approved: 3,
  committing: 4,
  committed: 4,
  rolled_back: 4,
  error: 1,
};

const ENTITY_OPTIONS = [
  { value: 'finance.Invoice', label: 'Opening AR (finance.Invoice)', guess: 'opening_ar' },
  { value: 'sales.Customer', label: 'Customer Master (sales.Customer)', guess: 'customer' },
  { value: 'procurement.Supplier', label: 'Supplier Master (procurement.Supplier)', guess: 'supplier' },
  { value: 'inventory.Product', label: 'Item Master (inventory.Product)', guess: 'item' },
];

const STORAGE_OPTIONS = [
  { value: 'column', label: 'Map to existing field' },
  { value: 'extra_data_new_field', label: 'Create new field (extra data)' },
  { value: 'ignore', label: 'Ignore column' },
];

const FALLBACK_JOB = {
  id: 'demo-job',
  migration_job_id: 'demo-job',
  entity_name_guess: 'supplier',
  target_model: 'procurement.Supplier',
  status: 'mapped',
  files: [
    {
      id: 'file-1',
      original_filename: 'supplier_master.xlsx',
      status: 'parsed',
      row_count_detected: 135,
      uploaded_at: '2025-10-27T12:00:00Z',
    },
  ],
  field_mappings: [
    { id: 1, column_name_in_file: 'Vendor Name', target_entity_field: 'name', target_storage_mode: 'column', confidence_score: 0.92, is_required_match: true },
    { id: 2, column_name_in_file: 'Contact Person', target_entity_field: 'contact_name', target_storage_mode: 'column', confidence_score: 0.88, is_required_match: false },
    { id: 3, column_name_in_file: 'Email', target_entity_field: 'email', target_storage_mode: 'column', confidence_score: 0.86, is_required_match: false },
    { id: 4, column_name_in_file: 'Phone', target_entity_field: '', target_storage_mode: 'ignore', confidence_score: 0.0, is_required_match: false },
    { id: 5, column_name_in_file: 'Tax ID', target_entity_field: 'tax_id', target_storage_mode: 'extra_data_new_field', confidence_score: 0.71, is_required_match: false },
  ],
  column_profiles: [
    {
      column_name_in_file: 'Vendor Name',
      detected_data_type: 'text',
      inferred_field_name: 'vendor_name',
      sample_values: ['Dhaka Cotton Mills', 'ColorSync Ltd.'],
      stats: { unique: 135, nulls: 0 },
      confidence_score: 0.92,
    },
  ],
  validation_errors: [
    { id: 'val-1', error_code: 'MISSING_PHONE', error_message: '2 rows missing phone numbers', severity: 'soft', created_at: '2025-10-27T12:00:00Z' },
    { id: 'val-2', error_code: 'DUPLICATE_SUPPLIER', error_message: 'Duplicate vendor detected: Rapid Box Solutions', severity: 'hard', created_at: '2025-10-27T12:00:00Z' },
  ],
  staging_summary: {
    pending_validation: 0,
    valid: 133,
    invalid: 2,
    skipped: 0,
  },
  validation_summary: {
    valid: 133,
    invalid: 2,
  },
  meta: {
    detector: { entity_guess: 'supplier' },
  },
};

const DataMigration = () => {
  const { currentCompany } = useCompany();
  const [jobs, setJobs] = useState([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [jobDetail, setJobDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [creatingJob, setCreatingJob] = useState(false);
  const [fileUploading, setFileUploading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [mappingEditor, setMappingEditor] = useState({ open: false, mapping: null, saving: false });
  const [useFallback, setUseFallback] = useState(false);

  const companyIdIsBackend = useMemo(() => {
    if (!currentCompany) return false;
    const numericId = Number(currentCompany.id);
    return !Number.isNaN(numericId) && numericId > 0;
  }, [currentCompany]);

  const refreshJobDetail = useCallback(
    async (jobId = selectedJobId) => {
      if (!jobId || useFallback) {
        return;
      }
      setDetailLoading(true);
      try {
        const response = await getMigrationJob(jobId);
        setJobDetail(response.data);
      } catch (error) {
        console.error('Failed to load migration job detail:', error?.message);
        message.error('Failed to load migration job detail.');
      } finally {
        setDetailLoading(false);
      }
    },
    [selectedJobId, useFallback],
  );

  const loadJobs = useCallback(async (preferredId = null) => {
    if (!currentCompany) {
      return;
    }
    setJobsLoading(true);
    try {
      if (!companyIdIsBackend) {
        throw new Error('No backend company selected');
      }
      const response = await listMigrationJobs({ company: currentCompany.id });
      const payload = response.data?.results || response.data || [];
      setJobs(payload);
      if (payload.length > 0) {
        const initial =
          payload.find((job) => String(job.id) === String(preferredId ?? selectedJobId)) || payload[0];
        setSelectedJobId(initial.id);
        await refreshJobDetail(initial.id);
      } else {
        setSelectedJobId(null);
        setJobDetail(null);
      }
      setUseFallback(false);
    } catch (error) {
      console.warn('Falling back to demo migration data:', error?.message);
      setUseFallback(true);
      setJobs([FALLBACK_JOB]);
      setSelectedJobId(FALLBACK_JOB.id);
      setJobDetail(FALLBACK_JOB);
      message.info('Data migration API unavailable. Showing demo data.');
    } finally {
      setJobsLoading(false);
    }
  }, [companyIdIsBackend, currentCompany, refreshJobDetail, selectedJobId]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!useFallback && selectedJobId) {
      refreshJobDetail(selectedJobId);
    }
  }, [refreshJobDetail, selectedJobId, useFallback]);

  const handleCreateJob = async (values) => {
    if (!companyIdIsBackend) {
      message.warning('Switch to a backend company to create a migration job.');
      return;
    }
    setCreatingJob(true);
    try {
      const payload = {
        company_id: currentCompany.id,
        target_model: values.target_model,
        entity_name_guess:
          values.entity_name_guess ||
          ENTITY_OPTIONS.find((option) => option.value === values.target_model)?.guess ||
          '',
        meta: values.meta || {},
      };
      const response = await createMigrationJob(payload);
      message.success('Migration job created.');
      setSelectedJobId(response.data.id);
      await loadJobs(response.data.id);
    } catch (error) {
      console.error('Failed to create migration job:', error?.message);
      message.error('Failed to create migration job.');
    } finally {
      setCreatingJob(false);
    }
  };

  const runJobAction = async (actionFn, successMessage) => {
    if (!selectedJobId || useFallback) {
      return;
    }
    setActionLoading(true);
    try {
      await actionFn(selectedJobId);
      message.success(successMessage);
      await refreshJobDetail(selectedJobId);
      await loadJobs(selectedJobId);
    } catch (error) {
      console.error('Migration action failed:', error?.message);
      message.error(error?.response?.data?.detail || 'Migration action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const uploadProps = useMemo(
    () => ({
      showUploadList: false,
      customRequest: async ({ file, onSuccess, onError }) => {
        if (!selectedJobId || useFallback) {
          onError?.(new Error('No job selected'));
          return;
        }
        setFileUploading(true);
        try {
          await uploadMigrationFile(selectedJobId, file);
          message.success('File uploaded successfully.');
          onSuccess?.();
          await refreshJobDetail(selectedJobId);
        } catch (error) {
          console.error('File upload failed:', error?.message);
          message.error(error?.response?.data?.detail || 'File upload failed.');
          onError?.(error);
        } finally {
          setFileUploading(false);
        }
      },
    }),
    [refreshJobDetail, selectedJobId, useFallback],
  );

  const currentStepIndex = useMemo(() => {
    if (!jobDetail) return 0;
    return STATUS_STEP_MAP[jobDetail.status] ?? 0;
  }, [jobDetail]);

  const mappingColumns = useMemo(
    () => [
      {
        title: 'Source Column',
        dataIndex: 'column_name_in_file',
        key: 'column_name_in_file',
      },
      {
        title: 'Target Field',
        dataIndex: 'target_entity_field',
        key: 'target_entity_field',
        render: (value) => value || <Text type="secondary">Not mapped</Text>,
      },
      {
        title: 'Storage',
        dataIndex: 'target_storage_mode',
        key: 'target_storage_mode',
        render: (value) => {
          if (value === 'extra_data_new_field') return <Tag color="purple">New Field</Tag>;
          if (value === 'ignore') return <Tag color="orange">Ignored</Tag>;
          return <Tag color="blue">Column</Tag>;
        },
      },
      {
        title: 'Confidence',
        dataIndex: 'confidence_score',
        key: 'confidence_score',
        render: (value) =>
          typeof value === 'number' ? `${Math.round(value * 100)}%` : <Text type="secondary">N/A</Text>,
      },
      {
        title: 'Required',
        dataIndex: 'is_required_match',
        key: 'is_required_match',
        render: (value) => (value ? <Tag color="green">Required</Tag> : <Tag>Optional</Tag>),
      },
      {
        title: 'Action',
        key: 'action',
        render: (_, record) => (
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => setMappingEditor({ open: true, mapping: record, saving: false })}
            disabled={useFallback}
          >
            Edit
          </Button>
        ),
      },
    ],
    [useFallback],
  );

  const validationColumns = [
    { title: 'Code', dataIndex: 'error_code', key: 'error_code' },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (value) =>
        value === 'hard' ? <Tag color="red">Hard</Tag> : <Tag color="orange">Soft</Tag>,
    },
    { title: 'Message', dataIndex: 'error_message', key: 'error_message' },
    { title: 'Logged At', dataIndex: 'created_at', key: 'created_at' },
  ];

  const stagingSummaryItems = useMemo(() => {
    if (!jobDetail?.staging_summary) return [];
    return Object.entries(jobDetail.staging_summary).map(([status, count]) => ({
      label: status.replace(/_/g, ' ').toUpperCase(),
      count,
    }));
  }, [jobDetail]);

  const handleMappingSave = async (values) => {
    if (!mappingEditor.mapping) {
      return;
    }
    const payload = { ...values };
    if (typeof payload.new_field_definition_json === 'string') {
      const trimmed = payload.new_field_definition_json.trim();
      if (trimmed.length === 0) {
        payload.new_field_definition_json = null;
      } else {
        try {
          payload.new_field_definition_json = JSON.parse(trimmed);
        } catch (error) {
          message.error('New field definition must be valid JSON.');
          return;
        }
      }
    }
    setMappingEditor((prev) => ({ ...prev, saving: true }));
    try {
      await updateMapping(jobDetail.id, mappingEditor.mapping.id, payload);
      message.success('Mapping updated.');
      setMappingEditor({ open: false, mapping: null, saving: false });
      await refreshJobDetail(jobDetail.id);
    } catch (error) {
      console.error('Failed to update mapping:', error?.message);
      message.error(error?.response?.data?.detail || 'Failed to update mapping.');
      setMappingEditor((prev) => ({ ...prev, saving: false }));
    }
  };

  const renderActions = () => {
    if (!jobDetail || useFallback) {
      return null;
    }

    return (
      <Space wrap>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />} loading={fileUploading}>
            Upload File
          </Button>
        </Upload>
        <Button
          icon={<FileSearchOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(profileMigrationJob, 'Structure detected.')}
        >
          Detect & Map
        </Button>
        <Button
          icon={<ThunderboltOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(stageMigrationJob, 'Rows staged for validation.')}
        >
          Stage
        </Button>
        <Button
          icon={<AlertOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(validateMigrationJob, 'Validation complete.')}
        >
          Validate
        </Button>
        <Button
          icon={<CheckCircleOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(submitMigrationJob, 'Submitted for approval.')}
        >
          Submit
        </Button>
        <Button
          type="primary"
          icon={<CheckOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(approveMigrationJob, 'Migration approved.')}
        >
          Approve
        </Button>
        <Button
          type="primary"
          icon={<CloudSyncOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(commitMigrationJob, 'Migration committed.')}
        >
          Commit
        </Button>
        <Button
          danger
          icon={<CloseOutlined />}
          loading={actionLoading}
          onClick={() => runJobAction(rollbackMigrationJob, 'Rollback completed.')}
        >
          Rollback
        </Button>
      </Space>
    );
  };

  return (
    <div>
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={8}>
          <Card
            title="Create Migration Job"
            size="small"
            extra={
              <Button icon={<ReloadOutlined />} type="link" onClick={loadJobs} disabled={jobsLoading}>
                Refresh
              </Button>
            }
          >
            <Form layout="vertical" onFinish={handleCreateJob}>
              <Form.Item
                label="Target Model"
                name="target_model"
                rules={[{ required: true, message: 'Select a target model' }]}
              >
                <Select options={ENTITY_OPTIONS} placeholder="Select entity to migrate" />
              </Form.Item>
              <Form.Item label="Entity Alias" name="entity_name_guess">
                <Input placeholder="e.g., opening_ar" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" block loading={creatingJob} disabled={useFallback}>
                  Create Job
                </Button>
              </Form.Item>
            </Form>
          </Card>

          <Card title="Migration Jobs" size="small" style={{ marginTop: 16 }}>
            <Spin spinning={jobsLoading}>
              <List
                dataSource={jobs}
                locale={{ emptyText: 'No migration jobs yet.' }}
                renderItem={(item) => (
                  <List.Item
                    key={item.id}
                    onClick={() => {
                      setSelectedJobId(item.id);
                      if (!useFallback) {
                        refreshJobDetail(item.id);
                      } else {
                        setJobDetail(item);
                      }
                    }}
                    style={{
                      cursor: 'pointer',
                      background: String(item.id) === String(selectedJobId) ? '#f0f5ff' : undefined,
                      borderRadius: 6,
                      marginBottom: 8,
                      padding: 12,
                    }}
                  >
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space align="center">
                        <Text strong>{item.entity_name_guess || item.target_model}</Text>
                        <Tag color={item.status === 'committed' ? 'green' : item.status === 'error' ? 'red' : 'blue'}>
                          {item.status}
                        </Tag>
                      </Space>
                      <Text type="secondary" ellipsis>
                        {item.target_model}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Spin>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <Title level={4} style={{ margin: 0 }}>
                  {jobDetail ? jobDetail.entity_name_guess || jobDetail.target_model : 'Migration Detail'}
                </Title>
                {jobDetail ? <Tag color="blue">{jobDetail.status}</Tag> : null}
              </Space>
            }
            extra={renderActions()}
          >
            {detailLoading ? (
              <Spin />
            ) : jobDetail ? (
              <>
                <Steps
                  current={currentStepIndex}
                  items={STEP_ITEMS.map((item) => ({ title: item.title, icon: item.icon }))}
                  responsive
                />

                <Divider />

                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="Target Model">{jobDetail.target_model}</Descriptions.Item>
                  <Descriptions.Item label="Job ID">{jobDetail.migration_job_id}</Descriptions.Item>
                  <Descriptions.Item label="Created At">
                    {jobDetail.created_at ? new Date(jobDetail.created_at).toLocaleString() : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Company">{jobDetail.company_name || '—'}</Descriptions.Item>
                </Descriptions>

                <Divider />

                <Row gutter={[16, 16]}>
                  <Col span={24}>
                    <Card title="Source Files" size="small">
                      <List
                        dataSource={jobDetail.files || []}
                        locale={{ emptyText: 'No files uploaded yet.' }}
                        renderItem={(file) => (
                          <List.Item key={file.id}>
                            <Space>
                              <FileOutlined />
                              <Text>{file.original_filename}</Text>
                              <Tag>{file.status}</Tag>
                              <Text type="secondary">
                                {file.row_count_detected ? `${file.row_count_detected} rows` : '—'}
                              </Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </Card>
                  </Col>

                  <Col span={24}>
                    <Card title="Field Mapping" size="small">
                      <Table
                        rowKey="id"
                        dataSource={jobDetail.field_mappings || []}
                        columns={mappingColumns}
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  </Col>

                  <Col span={24}>
                    <Card title="Validation Results" size="small">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {jobDetail.validation_summary ? (
                          <Space>
                            <Tag color="green">Valid: {jobDetail.validation_summary.valid ?? 0}</Tag>
                            <Tag color="red">Invalid: {jobDetail.validation_summary.invalid ?? 0}</Tag>
                          </Space>
                        ) : null}
                        <Table
                          rowKey="id"
                          dataSource={jobDetail.validation_errors || []}
                          columns={validationColumns}
                          size="small"
                          pagination={false}
                        />
                      </Space>
                    </Card>
                  </Col>

                  <Col span={24}>
                    <Card title="Staging Summary" size="small">
                      <List
                        grid={{ gutter: 16, column: 4 }}
                        dataSource={stagingSummaryItems}
                        locale={{ emptyText: 'Staging not run yet.' }}
                        renderItem={(item) => (
                          <List.Item key={item.label}>
                            <Card size="small" bordered>
                              <Space direction="vertical" size={0}>
                                <Text type="secondary">{item.label}</Text>
                                <Title level={4} style={{ margin: 0 }}>
                                  {item.count}
                                </Title>
                              </Space>
                            </Card>
                          </List.Item>
                        )}
                      />
                    </Card>
                  </Col>
                </Row>
              </>
            ) : (
              <Empty description="Select a migration job to see details." />
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        open={mappingEditor.open}
        title="Edit Field Mapping"
        onCancel={() => setMappingEditor({ open: false, mapping: null, saving: false })}
        destroyOnClose
        footer={null}
      >
        {mappingEditor.mapping ? (
          <Form
            layout="vertical"
            initialValues={{
              target_entity_field: mappingEditor.mapping.target_entity_field,
              target_storage_mode: mappingEditor.mapping.target_storage_mode,
              is_required_match: mappingEditor.mapping.is_required_match,
              new_field_definition_json: mappingEditor.mapping.new_field_definition_json,
            }}
            onFinish={handleMappingSave}
          >
            <Form.Item label="Source Column">
              <Input value={mappingEditor.mapping.column_name_in_file} disabled />
            </Form.Item>
            <Form.Item
              label="Target Field"
              name="target_entity_field"
              rules={[{ required: mappingEditor.mapping.target_storage_mode !== 'ignore', message: 'Provide a target field name' }]}
            >
              <Input placeholder="e.g., customer_code" />
            </Form.Item>
            <Form.Item label="Storage Mode" name="target_storage_mode">
              <Select options={STORAGE_OPTIONS} />
            </Form.Item>
            <Form.Item label="Mark as required" name="is_required_match" valuePropName="checked">
              <Switch checkedChildren="Required" unCheckedChildren="Optional" />
            </Form.Item>
            <Form.Item label="New Field Definition (JSON)" name="new_field_definition_json">
              <Input.TextArea rows={3} placeholder='{"field_name": "region_code", "layer": "COMPANY_OVERRIDE"}' />
            </Form.Item>
            <Form.Item>
              <Space style={{ justifyContent: 'flex-end', width: '100%' }}>
                <Button onClick={() => setMappingEditor({ open: false, mapping: null, saving: false })}>
                  Cancel
                </Button>
                <Button type="primary" htmlType="submit" loading={mappingEditor.saving}>
                  Save Mapping
                </Button>
              </Space>
            </Form.Item>
          </Form>
        ) : null}
      </Modal>
    </div>
  );
};

export default DataMigration;
