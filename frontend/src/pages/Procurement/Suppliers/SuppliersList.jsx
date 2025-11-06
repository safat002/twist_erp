import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Space,
  Segmented,
  Input,
  Tag,
  Statistic,
  Typography,
  List,
  Button,
  Modal,
  Form,
  Select,
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
      await api.post('/api/v1/procurement/suppliers/', values);
      message.success('Supplier added successfully!');
      handleCancel();
      loadSuppliers();
    } catch (error) {
      message.error('Failed to add supplier.');
    }
  };

  const loadAccounts = async () => {
    try {
      setAccountsLoading(true);
      const res = await api.get('/api/v1/finance/accounts/');
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

      <Modal title="Add New Supplier" open={isModalVisible} onCancel={handleCancel} footer={null} destroyOnHidden>
        <Form form={form} layout="vertical" onFinish={handleFormSubmit} initialValues={{ supplier_type: 'local' }}>
          <Form.Item name="name" label="Supplier Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Form.Item name="phone" label="Phone">
            <Input />
          </Form.Item>
          <Form.Item name="payable_account" label="Payable Account (optional)"> 
            <Select loading={accountsLoading} placeholder="Select payable account (defaults to A/P)" showSearch optionFilterProp="label" allowClear>
              {(accounts || []).map((acc) => (
                <Select.Option key={acc.id} value={acc.id} label={`${acc.code} - ${acc.name}`}>
                  {acc.code} - {acc.name}
                </Select.Option>
              ))}
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
          <Form.Item>
            <Button type="primary" htmlType="submit">Submit</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SuppliersList;


