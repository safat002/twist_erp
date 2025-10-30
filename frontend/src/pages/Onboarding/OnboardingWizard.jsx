import React, { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Result,
  Row,
  Space,
  Steps,
  Switch,
  Typography,
} from 'antd';
import api from '../../services/api';

const { Title, Text } = Typography;

const industryPacks = [
  { label: 'Manufacturing / Garments', value: 'manufacturing' },
  { label: 'NGO / Donor-Funded', value: 'ngo' },
  { label: 'Trading & Distribution', value: 'trading' },
  { label: 'Retail / POS', value: 'retail' },
  { label: 'Services / Telco', value: 'services' },
];

const initialGroup = {
  group_name: '',
  industry_pack_type: '',
  supports_intercompany: true,
};

const initialCompany = {
  code: '',
  name: '',
  legal_name: '',
  currency_code: 'USD',
  fiscal_year_start: null,
  tax_id: '',
  registration_number: '',
};

const OnboardingWizard = () => {
  const [current, setCurrent] = useState(0);
  const [groupForm] = Form.useForm();
  const [companyForm] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const steps = useMemo(
    () => [
      {
        title: 'Company Group',
        description: 'Describe the tenant you want to provision.',
      },
      {
        title: 'Default Company',
        description: 'Configure the first legal entity in this tenant.',
      },
      {
        title: 'Review & Provision',
        description: 'Confirm details and launch the provisioning flow.',
      },
    ],
    [],
  );

  const next = async () => {
    if (current === 0) {
      try {
        await groupForm.validateFields();
        setCurrent(current + 1);
      } catch (validationError) {
        // handled by form
      }
      return;
    }

    if (current === 1) {
      try {
        await companyForm.validateFields();
        setCurrent(current + 1);
      } catch (validationError) {
        // handled by form
      }
      return;
    }
  };

  const prev = () => {
    setCurrent((index) => Math.max(index - 1, 0));
  };

  const resetWizard = () => {
    groupForm.resetFields();
    companyForm.resetFields();
    setCurrent(0);
    setResult(null);
    setError(null);
  };

  const handleProvision = async () => {
    try {
      const groupValues = await groupForm.validateFields();
      const companyValues = await companyForm.validateFields();

      setSubmitting(true);
      setError(null);

      const payload = {
        ...groupValues,
        company: {
          ...companyValues,
          fiscal_year_start: companyValues.fiscal_year_start
            ? companyValues.fiscal_year_start.format('YYYY-MM-DD')
            : null,
        },
      };

      const response = await api.post('/api/v1/companies/provision/', payload);
      setResult(response.data);
      setCurrent(steps.length - 1);
    } catch (err) {
      if (err?.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(err?.message || 'Provisioning failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const renderGroupStep = () => (
    <Card title="Company Group Details">
      <Form layout="vertical" form={groupForm} initialValues={initialGroup}>
        <Form.Item
          label="Company Group Name"
          name="group_name"
          rules={[{ required: true, message: 'Please provide a company group name.' }]}
        >
          <Input placeholder="e.g., Twist Holdings" />
        </Form.Item>
        <Form.Item label="Industry Pack" name="industry_pack_type">
          <Input list="industry_packs" placeholder="Select or type an industry pack value" />
          <datalist id="industry_packs">
            {industryPacks.map((pack) => (
              <option key={pack.value} value={pack.value}>
                {pack.label}
              </option>
            ))}
          </datalist>
        </Form.Item>
        <Form.Item
          label="Supports inter-company transactions"
          name="supports_intercompany"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Card>
  );

  const renderCompanyStep = () => (
    <Card title="Default Company Setup">
      <Form layout="vertical" form={companyForm} initialValues={initialCompany}>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Company Code"
              name="code"
              rules={[
                { required: true, message: 'A company code is required.' },
                { pattern: /^[A-Z0-9]+$/, message: 'Use uppercase letters and numbers only.' },
              ]}
            >
              <Input placeholder="TWISTHQ" />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="Display Name"
              name="name"
              rules={[{ required: true, message: 'Please provide a display name.' }]}
            >
              <Input placeholder="Twist Head Office" />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item
          label="Legal Name"
          name="legal_name"
          rules={[{ required: true, message: 'Please provide a legal name.' }]}
        >
          <Input placeholder="Twist Head Office Ltd." />
        </Form.Item>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Currency"
              name="currency_code"
              rules={[{ required: true, message: 'Please provide the base currency.' }]}
            >
              <Input placeholder="USD" maxLength={3} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item
              label="Fiscal Year Start"
              name="fiscal_year_start"
              rules={[{ required: true, message: 'Please choose the start of the fiscal year.' }]}
            >
              <DatePicker picker="date" style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              label="Tax ID"
              name="tax_id"
              rules={[{ required: true, message: 'Please provide a tax ID.' }]}
            >
              <Input placeholder="TIN-..." />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="Registration Number" name="registration_number">
              <Input placeholder="Business registration number" />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Card>
  );

  const renderReviewStep = () => {
    const groupValues = groupForm.getFieldsValue();
    const companyValues = companyForm.getFieldsValue();
    return (
      <Card title="Review Configuration">
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>Company Group</Title>
            <Text strong>Name:</Text> <Text>{groupValues.group_name || '--'}</Text>
            <br />
            <Text strong>Industry Pack:</Text>{' '}
            <Text>{groupValues.industry_pack_type || 'Not specified'}</Text>
            <br />
            <Text strong>Inter-company:</Text>{' '}
            <Text>{groupValues.supports_intercompany ? 'Enabled' : 'Disabled'}</Text>
          </div>
          <div>
            <Title level={4}>Default Company</Title>
            <Text strong>Code:</Text> <Text>{companyValues.code || '--'}</Text>
            <br />
            <Text strong>Name:</Text> <Text>{companyValues.name || '--'}</Text>
            <br />
            <Text strong>Legal Name:</Text> <Text>{companyValues.legal_name || '--'}</Text>
            <br />
            <Text strong>Currency:</Text> <Text>{companyValues.currency_code || '--'}</Text>
            <br />
            <Text strong>Fiscal Year Start:</Text>{' '}
            <Text>
              {companyValues.fiscal_year_start
                ? companyValues.fiscal_year_start.format('YYYY-MM-DD')
                : '--'}
            </Text>
          </div>
          {error ? <Alert type="error" showIcon message={error} /> : null}
          {result ? (
            <Result
              status="success"
              title="Provisioning complete"
              subTitle={`Company Group ${result.company_group.name} is ready.`}
            />
          ) : (
            <Alert
              type="info"
              showIcon
              message="Provisioning will create the database, run migrations, and bootstrap your first company."
            />
          )}
        </Space>
      </Card>
    );
  };

  return (
    <div>
      <Title level={2}>Tenant Onboarding</Title>
      <Text type="secondary">
        Launch a new CompanyGroup, provision its database, and create the first legal entity.
      </Text>
      <Steps current={current} items={steps} style={{ marginTop: 24, marginBottom: 24 }} />

      <div style={{ minHeight: 360 }}>
        {current === 0 && renderGroupStep()}
        {current === 1 && renderCompanyStep()}
        {current === 2 && renderReviewStep()}
      </div>

      <div style={{ marginTop: 24 }}>
        <Space>
          {current > 0 && (
            <Button onClick={prev} disabled={submitting}>
              Previous
            </Button>
          )}
          {current < steps.length - 1 && (
            <Button type="primary" onClick={next}>
              Next
            </Button>
          )}
          {current === steps.length - 1 && !result && (
            <Button type="primary" loading={submitting} onClick={handleProvision}>
              Provision Tenant
            </Button>
          )}
          {current === steps.length - 1 && result ? (
            <Button onClick={resetWizard}>Start Another Tenant</Button>
          ) : null}
        </Space>
      </div>
    </div>
  );
};

export default OnboardingWizard;

