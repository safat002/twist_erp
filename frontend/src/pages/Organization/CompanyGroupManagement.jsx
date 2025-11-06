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
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { companyGroupService } from '../../services/organization';
import api from '../../services/api';

const { Title } = Typography;
const { TextArea } = Input;

const CompanyGroupManagement = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isViewModalVisible, setIsViewModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [viewingGroup, setViewingGroup] = useState(null);
  const [form] = Form.useForm();
  const [packOptions, setPackOptions] = useState([]);

  useEffect(() => {
    loadGroups();
    loadIndustryPacks();
  }, []);

  useEffect(() => {
    if (editingGroup) {
      form.setFieldsValue(editingGroup);
    } else {
      form.resetFields();
    }
  }, [editingGroup, form]);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const response = await companyGroupService.list();
      setGroups(response.data.results || response.data || []);
    } catch (error) {
      message.error('Failed to load company groups');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadIndustryPacks = async () => {
    try {
      const res = await api.get('/metadata/definitions/', { params: { status: 'active' } });
      const defs = res?.data?.results || res?.data || [];
      const packs = Array.from(
        new Set(
          defs
            .filter((d) => d.layer === 'INDUSTRY_PACK' && d.summary && (d.summary.industry_pack || d.summary.industry || d.summary.pack))
            .map((d) => String(d.summary.industry_pack || d.summary.industry || d.summary.pack)),
        ),
      ).sort();
      setPackOptions(packs);
    } catch (e) {
      // Non-fatal; keep empty
    }
  };

  const showCreateModal = () => {
    setEditingGroup(null);
    setIsModalVisible(true);
  };

  const showEditModal = (group) => {
    setEditingGroup(group);
    setIsModalVisible(true);
  };

  const showViewModal = async (group) => {
    try {
      const response = await companyGroupService.get(group.id);
      setViewingGroup(response.data);
      setIsViewModalVisible(true);
    } catch (error) {
      message.error('Failed to load group details');
    }
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setEditingGroup(null);
    form.resetFields();
  };

  const handleViewCancel = () => {
    setIsViewModalVisible(false);
    setViewingGroup(null);
  };

  const handleFormSubmit = async (values) => {
    try {
      if (editingGroup) {
        await companyGroupService.patch(editingGroup.id, values);
        message.success('Company group updated successfully');
      } else {
        await companyGroupService.create(values);
        message.success('Company group created successfully');
      }
      handleCancel();
      loadGroups();
    } catch (error) {
      message.error(`Failed to ${editingGroup ? 'update' : 'create'} company group`);
      console.error(error);
    }
  };

  const handleDelete = async (id) => {
    try {
      await companyGroupService.delete(id);
      message.success('Company group deleted successfully');
      loadGroups();
    } catch (error) {
      const status = error?.response?.status;
      const data = error?.response?.data;
      if (status === 409 && data?.companies) {
        const names = data.companies.map((c) => `${c.code || ''} ${c.name}`).join(', ');
        Modal.warning({
          title: 'Cannot delete company group',
          content: (
            <div>
              <p>{data?.error || 'This group has companies. Delete companies first.'}</p>
              <p><strong>Affected:</strong> {names}</p>
            </div>
          ),
        });
      } else {
        message.error('Failed to delete company group');
      }
    }
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      width: 100,
      render: (code) => code || '-',
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Type',
      dataIndex: 'group_type',
      key: 'group_type',
      width: 150,
      render: (type) => {
        const colors = {
          holding: 'blue',
          consortium: 'green',
          ngo_umbrella: 'purple',
          franchise: 'orange',
          group_of_companies: 'geekblue',
          other: 'default',
        };
        const labels = {
          holding: 'Holding',
          consortium: 'Consortium',
          ngo_umbrella: 'NGO Umbrella',
          franchise: 'Franchise',
          group_of_companies: 'Group of Companies',
          other: 'Other',
        };
        return <Tag color={colors[type]}>{labels[type] || type}</Tag>;
      },
    },
    {
      title: 'Companies',
      dataIndex: 'companies_count',
      key: 'companies_count',
      width: 100,
      align: 'center',
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
            title="Are you sure you want to delete this company group?"
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
      <Title level={2}>Company Group Management</Title>
      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreateModal}>
            Create Company Group
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadGroups} loading={loading}>
            Refresh
          </Button>
        </Space>
        <Table
          columns={columns}
          dataSource={groups}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingGroup ? 'Edit Company Group' : 'Create Company Group'}
        open={isModalVisible}
        onCancel={handleCancel}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleFormSubmit}>
          <Form.Item name="code" label="Group Code">
            <Input placeholder="Auto-generated" disabled />
          </Form.Item>

          <Form.Item
            name="name"
            label="Group Name"
            rules={[{ required: true, message: 'Please enter group name' }]}
          >
            <Input placeholder="e.g., My Company Group" />
          </Form.Item>

          <Form.Item name="group_type" label="Group Type" initialValue="holding">
            <Select>
              <Select.Option value="holding">Holding Company</Select.Option>
              <Select.Option value="consortium">Consortium/Association</Select.Option>
              <Select.Option value="ngo_umbrella">NGO Umbrella Organization</Select.Option>
              <Select.Option value="franchise">Franchise Network</Select.Option>
              <Select.Option value="group_of_companies">Group of Companies</Select.Option>
              <Select.Option value="other">Other</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={3} placeholder="Brief description of the company group" />
          </Form.Item>

          <Form.Item name="base_currency" label="Base Currency" initialValue="USD">
            <Select showSearch optionFilterProp="children">
              {[
                'USD','EUR','GBP','BDT','INR','PKR','LKR','CNY','JPY','AUD','CAD','SGD','MYR','THB','IDR','PHP','AED','SAR','KWD','OMR','QAR','ZAR','NGN','GHS','KES',
              ].map((c) => (
                <Select.Option key={c} value={c}>{c}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="fiscal_year_end_month" label="Fiscal Year End Month" initialValue={12}>
            <Select>
              {[
                [1,'January'],[2,'February'],[3,'March'],[4,'April'],[5,'May'],[6,'June'],[7,'July'],[8,'August'],[9,'September'],[10,'October'],[11,'November'],[12,'December'],
              ].map(([v,l]) => (
                <Select.Option key={v} value={v}>{l}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="industry_pack_type" label="Industry Pack">
            <Select allowClear placeholder="Select industry pack" loading={!packOptions.length}>
              {packOptions.map((p) => (
                <Select.Option key={p} value={p}>{p}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="owner_name" label="Owner Name">
            <Input placeholder="Owner full name" />
          </Form.Item>

          <Form.Item name="owner_email" label="Owner Email">
            <Input type="email" placeholder="owner@example.com" />
          </Form.Item>

          <Form.Item name="owner_phone" label="Owner Phone">
            <Input placeholder="+1234567890" />
          </Form.Item>

          <Form.Item name="tax_id" label="Tax ID">
            <Input placeholder="Tax identification number" />
          </Form.Item>

          <Form.Item name="registration_number" label="Registration Number">
            <Input placeholder="Company registration number" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingGroup ? 'Update' : 'Create'}
              </Button>
              <Button onClick={handleCancel}>Cancel</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* View Details Modal */}
      <Modal
        title="Company Group Details"
        open={isViewModalVisible}
        onCancel={handleViewCancel}
        footer={[
          <Button key="close" onClick={handleViewCancel}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {viewingGroup && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Code">{viewingGroup.code || '-'}</Descriptions.Item>
            <Descriptions.Item label="Name">{viewingGroup.name}</Descriptions.Item>
            <Descriptions.Item label="Type">
              {viewingGroup.group_type?.replace('_', ' ')?.toUpperCase()}
            </Descriptions.Item>
            <Descriptions.Item label="Base Currency">
              {viewingGroup.base_currency}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={viewingGroup.is_active ? 'success' : 'default'}>
                {viewingGroup.is_active ? 'Active' : 'Inactive'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Companies Count">
              {viewingGroup.companies_count || 0}
            </Descriptions.Item>
            <Descriptions.Item label="Description" span={2}>
              {viewingGroup.description || 'No description provided'}
            </Descriptions.Item>
            {viewingGroup.owner_name && (
              <Descriptions.Item label="Owner">{viewingGroup.owner_name}</Descriptions.Item>
            )}
            {viewingGroup.owner_email && (
              <Descriptions.Item label="Owner Email">{viewingGroup.owner_email}</Descriptions.Item>
            )}
            {viewingGroup.tax_id && (
              <Descriptions.Item label="Tax ID">{viewingGroup.tax_id}</Descriptions.Item>
            )}
            {viewingGroup.registration_number && (
              <Descriptions.Item label="Registration Number">
                {viewingGroup.registration_number}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default CompanyGroupManagement;
