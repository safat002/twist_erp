import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Popconfirm,
  Tag,
  Descriptions,
  Switch,
  InputNumber,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { branchService, companyService, organizationHelpers } from '../../services/organization';
import { useCompany } from '../../contexts/CompanyContext';

const { Title } = Typography;

const BranchManagement = () => {
  const { currentCompany } = useCompany();
  const [branches, setBranches] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isViewModalVisible, setIsViewModalVisible] = useState(false);
  const [editingBranch, setEditingBranch] = useState(null);
  const [viewingBranch, setViewingBranch] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadCompanies();
    loadBranches();
  }, []);

  useEffect(() => {
    if (editingBranch) {
      form.setFieldsValue(editingBranch);
    } else {
      form.resetFields();
      if (currentCompany) {
        form.setFieldsValue({ company: currentCompany.id });
      }
    }
  }, [editingBranch, currentCompany, form]);

  const loadCompanies = async () => {
    try {
      const response = await companyService.listMinimal();
      setCompanies(response.data || []);
    } catch (error) {
      console.error('Failed to load companies:', error);
    }
  };

  const loadBranches = async () => {
    try {
      setLoading(true);
      const response = await branchService.list();
      setBranches(response.data.results || response.data || []);
    } catch (error) {
      message.error('Failed to load branches');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const showCreateModal = () => {
    setEditingBranch(null);
    setIsModalVisible(true);
  };

  const showEditModal = (branch) => {
    setEditingBranch(branch);
    setIsModalVisible(true);
  };

  const showViewModal = async (branch) => {
    try {
      const response = await branchService.get(branch.id);
      setViewingBranch(response.data);
      setIsViewModalVisible(true);
    } catch (error) {
      message.error('Failed to load branch details');
    }
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setEditingBranch(null);
    form.resetFields();
  };

  const handleViewCancel = () => {
    setIsViewModalVisible(false);
    setViewingBranch(null);
  };

  const handleFormSubmit = async (values) => {
    try {
      if (editingBranch) {
        await branchService.update(editingBranch.id, values);
        message.success('Branch updated successfully');
      } else {
        await branchService.create(values);
        message.success('Branch created successfully');
      }
      handleCancel();
      loadBranches();
    } catch (error) {
      message.error(`Failed to ${editingBranch ? 'update' : 'create'} branch`);
      console.error(error);
    }
  };

  const handleDelete = async (id) => {
    try {
      await branchService.delete(id);
      message.success('Branch deleted successfully');
      loadBranches();
    } catch (error) {
      message.error('Failed to delete branch');
      console.error(error);
    }
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      width: 100,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Company',
      dataIndex: ['company', 'name'],
      key: 'company',
      width: 150,
    },
    {
      title: 'Type',
      dataIndex: 'branch_type',
      key: 'branch_type',
      width: 150,
      render: (type) => {
        const label = organizationHelpers.getBranchTypeLabel(type);
        return <Tag>{label}</Tag>;
      },
    },
    {
      title: 'Location',
      key: 'location',
      width: 200,
      render: (_, record) => organizationHelpers.formatBranchLocation(record),
    },
    {
      title: 'Active',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      align: 'center',
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showViewModal(record)}
            size="small"
          >
            View
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => showEditModal(record)}
            size="small"
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this branch?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small">
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Title level={2}>Branch Management</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreateModal}>
            Create Branch
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadBranches} loading={loading}>
            Refresh
          </Button>
        </Space>
        <Table
          columns={columns}
          dataSource={branches}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingBranch ? 'Edit Branch' : 'Create Branch'}
        open={isModalVisible}
        onCancel={handleCancel}
        footer={null}
        width={800}
      >
        <Form form={form} layout="vertical" onFinish={handleFormSubmit}>
          <Form.Item
            name="company"
            label="Company"
            rules={[{ required: true, message: 'Please select a company' }]}
          >
            <Select placeholder="Select company">
              {companies.map((company) => (
                <Select.Option key={company.id} value={company.id}>
                  {company.code ? `[${company.code}] ` : ''}{company.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="code"
            label="Branch Code"
            rules={[{ required: true, message: 'Please enter branch code' }]}
          >
            <Input placeholder="e.g., BR001" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Branch Name"
            rules={[{ required: true, message: 'Please enter branch name' }]}
          >
            <Input placeholder="e.g., Main Branch" />
          </Form.Item>

          <Form.Item
            name="branch_type"
            label="Branch Type"
            initialValue="office"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="headquarters">Headquarters</Select.Option>
              <Select.Option value="factory">Factory/Manufacturing</Select.Option>
              <Select.Option value="warehouse">Warehouse</Select.Option>
              <Select.Option value="retail">Retail Store</Select.Option>
              <Select.Option value="office">Office</Select.Option>
              <Select.Option value="regional">Regional Office</Select.Option>
              <Select.Option value="distribution">Distribution Center</Select.Option>
              <Select.Option value="other">Other</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="location" label="Location Address">
            <Input placeholder="Full address" />
          </Form.Item>

          <Form.Item name="city" label="City">
            <Input placeholder="City name" />
          </Form.Item>

          <Form.Item name="state_province" label="State/Province">
            <Input placeholder="State or province" />
          </Form.Item>

          <Form.Item name="country" label="Country">
            <Input placeholder="Country name" />
          </Form.Item>

          <Form.Item name="postal_code" label="Postal Code">
            <Input placeholder="Postal/ZIP code" />
          </Form.Item>

          <Space>
            <Form.Item name="latitude" label="Latitude">
              <InputNumber
                placeholder="Latitude"
                step={0.000001}
                precision={6}
                style={{ width: 150 }}
              />
            </Form.Item>

            <Form.Item name="longitude" label="Longitude">
              <InputNumber
                placeholder="Longitude"
                step={0.000001}
                precision={6}
                style={{ width: 150 }}
              />
            </Form.Item>
          </Space>

          <Form.Item name="has_warehouse" label="Has Warehouse" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingBranch ? 'Update' : 'Create'}
              </Button>
              <Button onClick={handleCancel}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* View Details Modal */}
      <Modal
        title="Branch Details"
        open={isViewModalVisible}
        onCancel={handleViewCancel}
        footer={[
          <Button key="close" onClick={handleViewCancel}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {viewingBranch && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Code">{viewingBranch.code}</Descriptions.Item>
            <Descriptions.Item label="Name">{viewingBranch.name}</Descriptions.Item>
            <Descriptions.Item label="Company">
              {viewingBranch.company?.name}
            </Descriptions.Item>
            <Descriptions.Item label="Type">
              {organizationHelpers.getBranchTypeLabel(viewingBranch.branch_type)}
            </Descriptions.Item>
            <Descriptions.Item label="Location" span={2}>
              {viewingBranch.location || 'Not specified'}
            </Descriptions.Item>
            <Descriptions.Item label="City">{viewingBranch.city || '-'}</Descriptions.Item>
            <Descriptions.Item label="State/Province">
              {viewingBranch.state_province || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Country">{viewingBranch.country || '-'}</Descriptions.Item>
            <Descriptions.Item label="Postal Code">
              {viewingBranch.postal_code || '-'}
            </Descriptions.Item>
            {(viewingBranch.latitude || viewingBranch.longitude) && (
              <>
                <Descriptions.Item label="Latitude">
                  {viewingBranch.latitude || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Longitude">
                  {viewingBranch.longitude || '-'}
                </Descriptions.Item>
              </>
            )}
            <Descriptions.Item label="Has Warehouse">
              <Tag color={viewingBranch.has_warehouse ? 'success' : 'default'}>
                {viewingBranch.has_warehouse ? 'Yes' : 'No'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={viewingBranch.is_active ? 'success' : 'default'}>
                {viewingBranch.is_active ? 'Active' : 'Inactive'}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default BranchManagement;
