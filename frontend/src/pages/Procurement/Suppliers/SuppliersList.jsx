import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Space,
  Segmented,
  Input,
  InputNumber,
  Tag,
  Statistic,
  Typography,
  List,
  Button,
  Modal,
  Form,
  Select,
  Switch,
  message,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;

const SuppliersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [suppliers, setSuppliers] = useState([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [accounts, setAccounts] = useState([]);
  const [accountsLoading, setAccountsLoading] = useState(false);

  useEffect(() => {
    loadSuppliers();
  }, [currentCompany]);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      if (!currentCompany) return;
      const response = await api.get('/api/v1/procurement/suppliers/');
      const data = Array.isArray(response.data) ? response.data : response.data?.results || [];
      setSuppliers(data);
    } catch (error) {
      console.warn('Failed to load suppliers:', error?.message);
    } finally {
      setLoading(false);
    }
  };

  const showModal = () => {
    setIsModalVisible(true);
    loadAccounts();
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    form.resetFields();
  };

  const handleFormSubmit = async (values) => {
    try {
      console.log('Submitting supplier data:', values);
      await api.post('/api/v1/procurement/suppliers/', values);
      message.success('Supplier added successfully!');
      handleCancel();
      loadSuppliers();
    } catch (error) {
      console.error('Supplier creation error - Full error:', error);
      console.error('Error response:', error?.response);
      console.error('Error response data:', error?.response?.data);

      // Extract error message from various possible structures
      let errorMsg = 'Failed to add supplier.';

      if (error?.response?.data) {
        const data = error.response.data;

        // Check for specific field errors
        if (data.payable_account) {
          errorMsg = `Payable Account: ${Array.isArray(data.payable_account) ? data.payable_account[0] : data.payable_account}`;
        } else if (data.company) {
          errorMsg = `Company: ${Array.isArray(data.company) ? data.company[0] : data.company}`;
        } else if (data.name) {
          errorMsg = `Name: ${Array.isArray(data.name) ? data.name[0] : data.name}`;
        } else if (data.detail) {
          errorMsg = data.detail;
        } else if (data.non_field_errors) {
          errorMsg = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : data.non_field_errors;
        } else if (typeof data === 'string') {
          errorMsg = data;
        } else {
          // Show all errors
          errorMsg = Object.entries(data).map(([key, value]) => {
            const val = Array.isArray(value) ? value[0] : value;
            return `${key}: ${val}`;
          }).join(', ');
        }
      }

      message.error(errorMsg, 5);
    }
  };

  const loadAccounts = async () => {
    try {
      setAccountsLoading(true);
      const res = await api.get('/api/v1/finance/accounts/', {
        params: { account_type: 'liability' }
      });
      const data = Array.isArray(res.data) ? res.data : res.data?.results || [];
      setAccounts(data);
    } catch (err) {
      message.error('Unable to load accounts.');
    } finally {
      setAccountsLoading(false);
    }
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Phone', dataIndex: 'phone', key: 'phone' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (status) => <Tag>{status.toUpperCase()}</Tag> },
  ];

  return (
    <div>
      <Title level={2}>Suppliers</Title>
      <Card>
        <Button type="primary" icon={<PlusOutlined />} onClick={showModal} style={{ marginBottom: 16 }}>
          Add Supplier
        </Button>
        <Table dataSource={suppliers} columns={columns} rowKey="id" loading={loading} />
      </Card>

      <Modal title="Add New Supplier" open={isModalVisible} onCancel={handleCancel} footer={null} destroyOnClose>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFormSubmit}
          initialValues={{ supplier_type: 'local', status: 'active', payment_terms: 30, is_active: true }}
        >
          <Form.Item name="name" label="Supplier Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>
          <Form.Item
            name="payable_account"
            label="Payable Account"
            tooltip="Required if no default liability account exists"
            rules={[{ required: true, message: 'Please select a payable account' }]}
          >
            <Select loading={accountsLoading} placeholder="Select payable account or system will auto-assign" showSearch optionFilterProp="label" allowClear>
              {(accounts || []).map((acc) => (
                <Select.Option key={acc.id} value={acc.id} label={`${acc.code} - ${acc.name}`}>
                  {acc.code} - {acc.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="address" label="Address">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="payment_terms" label="Payment Terms (days)">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="Status">
            <Select>
              <Select.Option value="draft">Draft</Select.Option>
              <Select.Option value="active">Active</Select.Option>
              <Select.Option value="inactive">Inactive</Select.Option>
              <Select.Option value="blacklisted">Blacklisted</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="supplier_type" label="Supplier Type">
            <Select>
              <Select.Option value="local">Local</Select.Option>
              <Select.Option value="import">Import</Select.Option>
              <Select.Option value="service">Service</Select.Option>
              <Select.Option value="sub_contractor">Sub-Contractor</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">Submit</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SuppliersList;
