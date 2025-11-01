import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  message,
  Row,
  Select,
  Space,
  Spin,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  FileAddOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';

import { useCompany } from '../../contexts/CompanyContext';
import {
  CalculationBuilder,
  DatasetSelector,
  FieldConfigurator,
  FilterBuilder,
  PreviewTable,
  SortBuilder,
} from '../../components/ReportBuilder';
import {
  createReportDefinition,
  deleteReportDefinition,
  getReportDefinition,
  listReportDatasets,
  listReportDefinitions,
  previewReportDefinition,
  publishReportDefinition,
  updateReportDefinition,
} from '../../services/reportBuilderService';

const { Title, Paragraph, Text } = Typography;

const emptyReport = {
  id: null,
  name: 'Untitled Report',
  description: '',
  scope_type: 'COMPANY',
  layer: 'COMPANY_OVERRIDE',
  status: 'draft',
  required_permissions: ['can_build_reports'],
  summary: {},
  definition: {
    data_source: null,
    fields: [],
    filters: [],
    sorts: [],
    calculations: [],
    limit: 200,
  },
};

const ReportBuilderPage = () => {
  const { currentCompany } = useCompany();
  const [loadingDatasets, setLoadingDatasets] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [report, setReport] = useState(emptyReport);
  const [activeTab, setActiveTab] = useState('designer');
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [previewResult, setPreviewResult] = useState({ rows: [], fields: [], meta: {} });
  const [previewLoading, setPreviewLoading] = useState(false);

  const companyReady = currentCompany && Number.isInteger(Number(currentCompany.id));

  useEffect(() => {
    if (!companyReady) return;
    loadDatasets();
    loadReports();
  }, [companyReady]);

  const loadDatasets = async () => {
    setLoadingDatasets(true);
    try {
      const response = await listReportDatasets();
      const payload = response?.data?.results || [];
      setDatasets(payload);
    } catch (error) {
      console.error('Failed to load report datasets', error);
      message.error('Unable to load report datasets. Check permissions or try again later.');
    } finally {
      setLoadingDatasets(false);
    }
  };

  const loadReports = async () => {
    setLoadingReports(true);
    try {
      const response = await listReportDefinitions();
      const payload = response?.data?.results || response?.data || [];
      setReports(Array.isArray(payload) ? payload : []);
    } catch (error) {
      console.error('Failed to load report definitions', error);
      message.error('Unable to load saved reports.');
    } finally {
      setLoadingReports(false);
    }
  };

  const resetBuilder = () => {
    setReport(emptyReport);
    setPreviewResult({ rows: [], fields: [], meta: {} });
  };

  const updateReport = (updates) => {
    setReport((current) => ({
      ...current,
      ...updates,
    }));
  };

  const updateDefinition = (updates) => {
    setReport((current) => ({
      ...current,
      definition: {
        ...current.definition,
        ...updates,
      },
    }));
  };

  const handleDatasetSelect = (dataset) => {
    if (!dataset) return;
    updateDefinition({
      data_source: dataset,
      fields: [],
      filters: [],
      sorts: [],
      calculations: [],
    });
    setPreviewResult({ rows: [], fields: [], meta: {} });
    if (dataset.required_permissions?.length) {
      updateReport({ required_permissions: Array.from(new Set(dataset.required_permissions)) });
    }
    message.success(`Dataset "${dataset.label}" selected. Configure fields to continue.`);
  };

  const availableFields = useMemo(() => {
    const ds = report.definition?.data_source;
    if (!ds) return [];
    if (ds.fields && Array.isArray(ds.fields)) return ds.fields;
    const match = datasets.find((item) => matchDataset(item, ds));
    return match?.fields || [];
  }, [report.definition?.data_source, datasets]);

  const selectedFields = report.definition?.fields || [];
  const filters = report.definition?.filters || [];
  const sorts = report.definition?.sorts || [];
  const calculations = report.definition?.calculations || [];

  const normalizePayload = () => {
    const dataSource = report.definition?.data_source;
    if (!dataSource) {
      throw new Error('Select a dataset before saving the report.');
    }
    const payloadDataSource = {
      type: dataSource.type,
      key: dataSource.key,
      slug: dataSource.slug,
      model: dataSource.model,
      required_permissions: dataSource.required_permissions,
    };
    const payloadFields = selectedFields.map((field, index) => ({
      id: field.id || field.field || field.key || `field_${index}`,
      field: field.field || field.key,
      label: field.label || field.alias || field.field,
      alias: field.alias || field.field,
      source: field.source || { path: field.field || field.key },
    }));
    return {
      name: report.name,
      description: report.description,
      scope_type: report.scope_type,
      layer: report.layer,
      status: report.status,
      required_permissions: report.required_permissions,
      summary: report.summary || {},
      definition: {
        data_source: payloadDataSource,
        fields: payloadFields,
        filters,
        sorts,
        calculations,
        limit: report.definition?.limit || null,
      },
    };
  };

  const handleSave = async () => {
    if (!report.name.trim()) {
      message.warning('Give your report a name before saving.');
      return;
    }
    if (!report.definition?.data_source) {
      message.warning('Pick a data source before saving.');
      return;
    }
    if (!selectedFields.length) {
      message.warning('Select at least one field to include in the report.');
      return;
    }
    const payload = normalizePayload();
    setSaving(true);
    try {
      let response;
      if (report.id) {
        response = await updateReportDefinition(report.id, payload);
      } else {
        response = await createReportDefinition(payload);
      }
      const updated = normalizeReportResponse(response.data, datasets);
      setReport(updated);
      await loadReports();
      message.success('Report saved successfully.');
    } catch (error) {
      console.error('Failed to save report', error);
      const detail = error?.response?.data?.detail;
      message.error(detail || 'Unable to save the report right now.');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!report.id) {
      message.info('Save the report before publishing.');
      return;
    }
    setPublishing(true);
    try {
      const response = await publishReportDefinition(report.id);
      const updated = normalizeReportResponse(response.data, datasets);
      setReport(updated);
      await loadReports();
      message.success('Report published and metadata synced.');
    } catch (error) {
      console.error('Failed to publish report', error);
      message.error('Unable to publish report. Check permissions and try again.');
    } finally {
      setPublishing(false);
    }
  };

  const handlePreview = async () => {
    if (!report.id) {
      message.info('Save the report first, then run the preview.');
      return;
    }
    setPreviewLoading(true);
    try {
      const response = await previewReportDefinition(report.id, {
        limit: report.definition?.limit || undefined,
      });
      const rows = response?.data?.rows || [];
      const fieldsMeta = response?.data?.fields || [];
      const meta = response?.data?.meta || {};
      setPreviewResult({ rows, fields: fieldsMeta, meta });
      message.success(`Preview loaded with ${rows.length} rows.`);
    } catch (error) {
      console.error('Failed to preview report', error);
      message.error('Unable to run preview. Ensure the dataset has data and you have permission.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSelectReport = async (id) => {
    setActiveTab('designer');
    if (!id) {
      resetBuilder();
      return;
    }
    try {
      const response = await getReportDefinition(id);
      const normalized = normalizeReportResponse(response.data, datasets);
      setReport(normalized);
      message.success(`Loaded report "${normalized.name}".`);
    } catch (error) {
      console.error('Failed to load report', error);
      message.error('Unable to load the selected report.');
    }
  };

  const handleDeleteReport = async (id) => {
    try {
      await deleteReportDefinition(id);
      message.success('Report deleted.');
      if (report.id === id) {
        resetBuilder();
      }
      await loadReports();
    } catch (error) {
      console.error('Failed to delete report', error);
      message.error('Unable to delete report.');
    }
  };

  const limitOptions = [100, 250, 500, 1000];

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 24, width: '100%', justifyContent: 'space-between' }}>
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>
            Report Builder
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Assemble metadata-driven reports with drag-and-drop logic, governed by your ERP permissions.
          </Paragraph>
        </div>
        <Space>
          <Button icon={<FileAddOutlined />} onClick={resetBuilder}>
            New Report
          </Button>
          <Button icon={<SaveOutlined />} type="primary" loading={saving} onClick={handleSave}>
            Save
          </Button>
          <Button
            icon={<CloudUploadOutlined />}
            type="default"
            loading={publishing}
            onClick={handlePublish}
            disabled={!report.id}
          >
            Publish & Sync
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handlePreview} disabled={!report.id} loading={previewLoading}>
            Preview
          </Button>
        </Space>
      </Space>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane key="designer" tab="Designer">
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={16}>
              <Card bordered={false}>
                <Form layout="vertical">
                  <Form.Item label="Report Name" required>
                    <Input value={report.name} onChange={(event) => updateReport({ name: event.target.value })} />
                  </Form.Item>
                  <Form.Item label="Description">
                    <Input.TextArea
                      value={report.description}
                      rows={3}
                      onChange={(event) => updateReport({ description: event.target.value })}
                    />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item label="Scope">
                        <Select
                          value={report.scope_type}
                          onChange={(scope_type) => updateReport({ scope_type })}
                          options={[
                            { label: 'Company', value: 'COMPANY' },
                            { label: 'Company Group', value: 'GROUP' },
                            { label: 'Global', value: 'GLOBAL' },
                          ]}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="Layer">
                        <Select
                          value={report.layer}
                          onChange={(layer) => updateReport({ layer })}
                          options={[
                            { label: 'Company Override', value: 'COMPANY_OVERRIDE' },
                            { label: 'Group Custom', value: 'GROUP_CUSTOM' },
                            { label: 'Industry Pack', value: 'INDUSTRY_PACK' },
                            { label: 'Core', value: 'CORE' },
                          ]}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="Status">
                        <Select
                          value={report.status}
                          onChange={(status) => updateReport({ status })}
                          options={[
                            { label: 'Draft', value: 'draft' },
                            { label: 'Active', value: 'active' },
                            { label: 'Archived', value: 'archived' },
                          ]}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item label="Required Permissions">
                    <Select
                      mode="tags"
                      value={report.required_permissions}
                      onChange={(perms) => updateReport({ required_permissions: perms })}
                      tokenSeparators={[',', ' ']}
                      placeholder="Permission codes required to run this report"
                    />
                  </Form.Item>
                  <Form.Item label="Preview Limit">
                    <Select
                      value={report.definition?.limit}
                      onChange={(limit) => updateDefinition({ limit })}
                      allowClear
                      placeholder="Default preview limit"
                    >
                      {limitOptions.map((limit) => (
                        <Select.Option key={limit} value={limit}>
                          {limit} rows
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Form>
              </Card>

              <Divider />

              <Spin spinning={loadingDatasets} tip="Loading datasets...">
                <DatasetSelector
                  datasets={datasets}
                  value={report.definition?.data_source}
                  onSelect={handleDatasetSelect}
                  loading={loadingDatasets}
                />
              </Spin>

              <Divider dashed />

              <FieldConfigurator
                availableFields={availableFields}
                value={selectedFields}
                onChange={(fields) => updateDefinition({ fields })}
              />

              <Divider dashed />

              <FilterBuilder fields={selectedFields} value={filters} onChange={(items) => updateDefinition({ filters: items })} />

              <Divider dashed />

              <SortBuilder fields={selectedFields} value={sorts} onChange={(items) => updateDefinition({ sorts: items })} />

              <Divider dashed />

              <CalculationBuilder
                fields={selectedFields}
                value={calculations}
                onChange={(items) => updateDefinition({ calculations: items })}
              />
            </Col>

            <Col xs={24} lg={8}>
              <PreviewTable
                data={previewResult.rows}
                fields={previewResult.fields}
                loading={previewLoading}
                meta={previewResult.meta}
                onRefresh={handlePreview}
              />

              <Card bordered={false} style={{ marginTop: 24 }}>
                <Title level={5}>Report Metadata</Title>
                <Space direction="vertical" size="small">
                  <Text>
                    <strong>ID:</strong> {report.id || 'Not saved yet'}
                  </Text>
                  <Text>
                    <strong>Status:</strong>{' '}
                    <Tag color={report.status === 'active' ? 'green' : report.status === 'draft' ? 'blue' : 'default'}>
                      {report.status}
                    </Tag>
                  </Text>
                  <Text>
                    <strong>Dataset:</strong>{' '}
                    {report.definition?.data_source?.label || report.definition?.data_source?.key || 'None'}
                  </Text>
                  <Text>
                    <strong>Permissions:</strong>{' '}
                    {report.required_permissions.map((code) => (
                      <Tag key={code} color="purple">
                        {code}
                      </Tag>
                    ))}
                  </Text>
                  {report.last_published_at ? (
                    <Text>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
                      Published at {new Date(report.last_published_at).toLocaleString()}
                    </Text>
                  ) : (
                    <Text type="secondary">Not published yet.</Text>
                  )}
                </Space>
              </Card>
            </Col>
          </Row>
        </Tabs.TabPane>

        <Tabs.TabPane key="library" tab="Report Library">
          <Card bordered={false}>
            <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
              <Col>
                <Title level={4} style={{ marginBottom: 0 }}>
                  Saved Reports
                </Title>
                <Text type="secondary">Load or manage existing definitions.</Text>
              </Col>
              <Col>
                <Button icon={<ReloadOutlined />} onClick={loadReports} loading={loadingReports}>
                  Refresh
                </Button>
              </Col>
            </Row>
            <div style={{ overflowX: 'auto' }}>
              <table className="twist-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Scope</th>
                    <th>Updated</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {reports.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <Space direction="vertical" size={0}>
                          <Text strong>{item.name}</Text>
                          <Text type="secondary">{item.description}</Text>
                        </Space>
                      </td>
                      <td>
                        <Tag color={item.status === 'active' ? 'green' : item.status === 'draft' ? 'blue' : 'default'}>
                          {item.status}
                        </Tag>
                      </td>
                      <td>{item.scope_type}</td>
                      <td>{item.updated_at ? new Date(item.updated_at).toLocaleString() : '—'}</td>
                      <td>
                        <Space>
                          <Button size="small" onClick={() => handleSelectReport(item.id)}>
                            Load
                          </Button>
                          <Button size="small" danger onClick={() => handleDeleteReport(item.id)}>
                            Delete
                          </Button>
                        </Space>
                      </td>
                    </tr>
                  ))}
                  {reports.length === 0 && !loadingReports ? (
                    <tr>
                      <td colSpan={5}>
                        <Text type="secondary">No reports saved yet. Build one from the designer tab.</Text>
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

function matchDataset(candidate, dataSource) {
  if (!candidate || !dataSource) return false;
  if (candidate.key && dataSource.key && candidate.key === dataSource.key) return true;
  if (candidate.slug && dataSource.slug && candidate.slug === dataSource.slug) return true;
  return false;
}

function normalizeReportResponse(payload, datasets) {
  if (!payload) return emptyReport;
  const definition = payload.definition || {};
  const base = {
    id: payload.id,
    name: payload.name,
    description: payload.description || '',
    scope_type: payload.scope_type || 'COMPANY',
    layer: payload.layer || 'COMPANY_OVERRIDE',
    status: payload.status || 'draft',
    required_permissions: payload.required_permissions || ['can_build_reports'],
    summary: payload.summary || {},
    last_published_at: payload.last_published_at,
  };
  const datasetFromDefinition = definition.data_source || null;
  const datasetMatch = datasets.find((item) => matchDataset(item, datasetFromDefinition)) || datasetFromDefinition;

  const fields = (definition.fields || []).map((field, index) => ({
    id: field.id || field.field || field.key || `field_${index}`,
    field: field.field || field.key,
    label: field.label || field.alias || field.field,
    alias: field.alias || field.field,
    source: field.source || { path: field.field || field.key },
  }));

  return {
    ...emptyReport,
    ...base,
    definition: {
      data_source: datasetMatch,
      fields,
      filters: definition.filters || [],
      sorts: definition.sorts || [],
      calculations: definition.calculations || [],
      limit: definition.limit || 200,
    },
  };
}

export default ReportBuilderPage;
