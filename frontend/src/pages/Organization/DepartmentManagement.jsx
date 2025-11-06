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
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import {
  departmentService,
  companyService,
  branchService,
  organizationHelpers,
} from '../../services/organization';
import { useCompany } from '../../contexts/CompanyContext';

const { Title } = Typography;
const { TextArea } = Input;

const DepartmentManagement = () => {
  const { currentCompany } = useCompany();
  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isViewModalVisible, setIsViewModalVisible] = useState(false);
  const [editingDepartment, setEditingDepartment] = useState(null);
  const [viewingDepartment, setViewingDepartment] = useState(null);
  const [selectedCompanyId, setSelectedCompanyId] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadCompanies();
    loadDepartments();
  }, []);

  useEffect(() => {
    if (editingDepartment) {
      form.setFieldsValue(editingDepartment);
      if (editingDepartment.company) {
        loadBranchesForCompany(editingDepartment.company);
      }
    } else {
      form.resetFields();
      if (currentCompany) {
        form.setFieldsValue({ company: currentCompany.id });
        loadBranchesForCompany(currentCompany.id);
      }
    }
  }, [editingDepartment, currentCompany, form]);

  const loadCompanies = async () => {
    try {
      const response = await companyService.listMinimal();
      setCompanies(response.data || []);
    } catch (error) {
      console.error('Failed to load companies:', error);
    }
  };

  const loadBranchesForCompany = async (companyId) => {
    try {
      const response = await companyService.getBranches(companyId);
      setBranches(response.data || []);
    } catch (error) {
      console.error('Failed to load branches:', error);
      setBranches([]);
    }
  };

  const loadDepartments = async () => {
    try {
      setLoading(true);
      const response = await departmentService.list();
      setDepartments(response.data.results || response.data || []);
    } catch (error) {
      message.error('Failed to load departments');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const showCreateModal = () => {
    setEditingDepartment(null);
    setIsModalVisible(true);
  };

  const showEditModal = (department) => {
    setEditingDepartment(department);
    setIsModalVisible(true);
  };

  const showViewModal = async (department) => {
    try {
      const response = await departmentService.get(department.id);
      setViewingDepartment(response.data);
      setIsViewModalVisible(true);
    } catch (error) {
      message.error('Failed to load department details');
    }
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setEditingDepartment(null);
    form.resetFields();
  };

  const handleViewCancel = () => {
    setIsViewModalVisible(false);
    setViewingDepartment(null);
  };

  const handleCompanyChange = (companyId) => {
    setSelectedCompanyId(companyId);
    form.setFieldsValue({ branch: undefined });
    loadBranchesForCompany(companyId);
  };

  const handleFormSubmit = async (values) => {
    try {
      if (editingDepartment) {
        await departmentService.update(editingDepartment.id, values);
        message.success('Department updated successfully');
      } else {
        await departmentService.create(values);
        message.success('Department created successfully');
      }
      handleCancel();
      loadDepartments();
    } catch (error) {
      message.error(`Failed to ${editingDepartment ? 'update' : 'create'} department`);
      console.error(error);
    }
  };

  const handleDelete = async (id) => {
    try {
      await departmentService.delete(id);
      message.success('Department deleted successfully');
      loadDepartments();
    } catch (error) {
      message.error('Failed to delete department');
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
      title: 'Branch',
      dataIndex: ['branch', 'name'],
      key: 'branch',
      width: 150,
      render: (branchName) => branchName || '-',
    },
    {
      title: 'Type',
      dataIndex: 'department_type',
      key: 'department_type',
      width: 150,
      render: (type) => {
        const label = organizationHelpers.getDepartmentTypeLabel(type);
        return <Tag>{label}</Tag>;
      },
    },
    {
      title: 'Employees',
      dataIndex: 'employees_count',
      key: 'employees_count',
      width: 100,
      align: 'center',
      render: (count) => (
        <Space>
          <TeamOutlined />
          {count || 0}
        </Space>
      ),
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
            title="Are you sure you want to delete this department?"
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
      <Title level={2}>Department Management</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreateModal}>
            Create Department
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadDepartments} loading={loading}>
            Refresh
          </Button>
        </Space>
        <Table
          columns={columns}
          dataSource={departments}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingDepartment ? 'Edit Department' : 'Create Department'}
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
            <Select placeholder="Select company" onChange={handleCompanyChange}>
              {companies.map((company) => (
                <Select.Option key={company.id} value={company.id}>
                  {company.code ? `[${company.code}] ` : ''}{company.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="branch" label="Branch (Optional)">
            <Select placeholder="Select branch (if applicable)" allowClear>
              {branches.map((branch) => (
                <Select.Option key={branch.id} value={branch.id}>
                  {branch.code ? `[${branch.code}] ` : ''}{branch.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="code"
            label="Department Code"
            rules={[{ required: true, message: 'Please enter department code' }]}
          >
            <Input placeholder="e.g., DEPT001" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Department Name"
            rules={[{ required: true, message: 'Please enter department name' }]}
          >
            <Input placeholder="e.g., Finance Department" />
          </Form.Item>

          <Form.Item
            name="department_type"
            label="Department Type"
            initialValue="functional"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="operational">Operational</Select.Option>
              <Select.Option value="administrative">Administrative</Select.Option>
              <Select.Option value="functional">Functional</Select.Option>
              <Select.Option value="project">Project-Based</Select.Option>
              <Select.Option value="program">Program/Initiative</Select.Option>
              <Select.Option value="cost_center">Cost Center</Select.Option>
              <Select.Option value="other">Other</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Brief description of the department" />
          </Form.Item>

          <Form.Item name="cost_center_code" label="Cost Center Code">
            <Input placeholder="Accounting cost center code" />
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingDepartment ? 'Update' : 'Create'}
              </Button>
              <Button onClick={handleCancel}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* View Details Modal */}
      <Modal
        title="Department Details"
        open={isViewModalVisible}
        onCancel={handleViewCancel}
        footer={[
          <Button key="close" onClick={handleViewCancel}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {viewingDepartment && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Code">{viewingDepartment.code}</Descriptions.Item>
            <Descriptions.Item label="Name">{viewingDepartment.name}</Descriptions.Item>
            <Descriptions.Item label="Company">
              {viewingDepartment.company?.name}
            </Descriptions.Item>
            <Descriptions.Item label="Branch">
              {viewingDepartment.branch?.name || 'Not assigned to branch'}
            </Descriptions.Item>
            <Descriptions.Item label="Type">
              {organizationHelpers.getDepartmentTypeLabel(viewingDepartment.department_type)}
            </Descriptions.Item>
            <Descriptions.Item label="Employees">
              <Space>
                <TeamOutlined />
                {viewingDepartment.employees_count || 0}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="Description" span={2}>
              {viewingDepartment.description || 'No description provided'}
            </Descriptions.Item>
            {viewingDepartment.cost_center_code && (
              <Descriptions.Item label="Cost Center Code">
                {viewingDepartment.cost_center_code}
              </Descriptions.Item>
            )}
            {viewingDepartment.department_head && (
              <Descriptions.Item label="Department Head">
                {viewingDepartment.department_head.full_name || viewingDepartment.department_head.username}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="Status">
              <Tag color={viewingDepartment.is_active ? 'success' : 'default'}>
                {viewingDepartment.is_active ? 'Active' : 'Inactive'}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default DepartmentManagement;
