import React, { useState, useEffect } from 'react';
import { Card, Typography, Table, Button, Modal, Form, Input, Select, message, Space, DatePicker, Switch } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../../services/api';
import { useCompany } from '../../contexts/CompanyContext';

const { Title } = Typography;

const CompanyManagement = () => {
  const { companies, loading, refreshCompanies } = useCompany();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    if (editingCompany) {
      form.setFieldsValue(editingCompany);
    } else {
      form.resetFields();
    }
  }, [editingCompany, form]);

  const showCreateModal = () => {
    setEditingCompany(null);
    setIsModalVisible(true);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
  };

  const handleFormSubmit = async (values) => {
    try {
      // Provision a company group + default company in one go
      const payload = {
        group_name: values.group_name,
        industry_pack_type: values.industry_pack_type || '',
        supports_intercompany: Boolean(values.supports_intercompany),
        company: {
          code: values.code,
          name: values.name,
          legal_name: values.legal_name || values.name,
          currency_code: values.currency_code || 'BDT',
          fiscal_year_start: values.fiscal_year_start?.format('YYYY-MM-DD') || '2025-01-01',
          tax_id: values.tax_id || `TAX-${values.code}`,
          registration_number: values.registration_number || `REG-${values.code}`,
        },
      };
      await api.post('/api/v1/companies/provision/', payload);
      message.success('Company provisioned successfully!');
      handleCancel();
      refreshCompanies(); // Refresh the list of companies in context
    } catch (error) {
      message.error('Failed to provision company.');
    }
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Currency', dataIndex: 'currency_code', key: 'currency_code' },
  ];

  return (
    <>
      <Title level={2}>Company Management</Title>
      <Card>
        <Button type="primary" icon={<PlusOutlined />} onClick={showCreateModal} style={{ marginBottom: 16 }}>
          Add New Company
        </Button>
        <Table columns={columns} dataSource={companies} rowKey="id" loading={loading} />
      </Card>

      <Modal title={editingCompany ? 'Edit Company' : 'Provision Company'} open={isModalVisible} onCancel={handleCancel} footer={null}>
        <Form form={form} layout="vertical" onFinish={handleFormSubmit}>
          <Form.Item name="group_name" label="Company Group Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Twist Group" />
          </Form.Item>
          <Form.Item name="industry_pack_type" label="Industry Pack">
            <Select allowClear options={[
              { value: 'manufacturing', label: 'Manufacturing' },
              { value: 'trading', label: 'Trading' },
              { value: 'services', label: 'Services' },
              { value: 'ngo', label: 'NGO' },
            ]} />
          </Form.Item>
          <Form.Item name="supports_intercompany" label="Supports Intercompany" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="code" label="Company Code" rules={[{ required: true }]}>
            <Input placeholder="Unique code, e.g., HQ" />
          </Form.Item>
          <Form.Item name="name" label="Company Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="legal_name" label="Legal Name">
            <Input />
          </Form.Item>
          <Form.Item name="currency_code" label="Currency" initialValue="BDT">
            <Input placeholder="e.g., BDT, USD" />
          </Form.Item>
          <Form.Item name="fiscal_year_start" label="Fiscal Year Start" rules={[{ required: true }]}> 
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="tax_id" label="Tax ID">
            <Input />
          </Form.Item>
          <Form.Item name="registration_number" label="Registration Number">
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Provision</Button>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default CompanyManagement;
