import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Switch, message, Tag, Space } from 'antd';
import { PlusOutlined, ApartmentOutlined, FilterOutlined } from '@ant-design/icons';
import api from '../../services/api';
import { departmentService, branchService, organizationHelpers } from '../../services/organization';

const CostCenters = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // Department and Branch data
  const [departments, setDepartments] = useState([]);
  const [branches, setBranches] = useState([]);
  const [filterDepartment, setFilterDepartment] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/v1/budgets/cost-centers/');
      const list = Array.isArray(data) ? data : data?.results || [];
      setData(list);
    } catch (e) {
      message.error('Failed to load cost centers');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    loadDepartments();
    loadBranches();
  }, []);

  const loadDepartments = async () => {
    try {
      const response = await departmentService.list();
      setDepartments(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load departments:', error);
    }
  };

  const loadBranches = async () => {
    try {
      const response = await branchService.list();
      setBranches(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to load branches:', error);
    }
  };

  // Filter data by department
  const filteredData = useMemo(() => {
    if (!filterDepartment) return data;
    return data.filter((item) => item.department?.id === filterDepartment);
  }, [data, filterDepartment]);

  const columns = useMemo(
    () => [
      { title: 'Code', dataIndex: 'code', key: 'code', width: 120 },
      { title: 'Name', dataIndex: 'name', key: 'name' },
      {
        title: 'Department',
        dataIndex: ['department', 'name'],
        key: 'department',
        width: 200,
        render: (name, record) => (
          record.department ? (
            <Space>
              <ApartmentOutlined />
              <span>{name}</span>
            </Space>
          ) : (
            <Tag>No Department</Tag>
          )
        ),
      },
      {
        title: 'Branch',
        dataIndex: ['branch', 'name'],
        key: 'branch',
        width: 150,
        render: (name) => name || '-',
      },
      {
        title: 'Type',
        dataIndex: 'cost_center_type',
        key: 'cost_center_type',
        width: 150,
        render: (type) => <Tag color="blue">{type}</Tag>,
      },
      {
        title: 'Active',
        dataIndex: 'is_active',
        key: 'is_active',
        width: 80,
        align: 'center',
        render: (v) => <Tag color={v ? 'success' : 'default'}>{v ? 'Yes' : 'No'}</Tag>,
      },
    ],
    [],
  );

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await api.post('/api/v1/budgets/cost-centers/', {
        code: values.code,
        name: values.name,
        cost_center_type: values.cost_center_type || 'department',
        description: values.description || '',
        default_currency: values.default_currency || 'BDT',
        department: values.department || null,
        branch: values.branch || null,
        is_active: values.is_active ?? true,
      });
      message.success('Cost center created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return;
      const detail = e?.response?.data?.detail || 'Could not create cost center';
      message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="Cost Centers"
      extra={
        <Space>
          <Select
            style={{ width: 250 }}
            placeholder={
              <span>
                <FilterOutlined /> Filter by Department
              </span>
            }
            allowClear
            value={filterDepartment}
            onChange={setFilterDepartment}
            showSearch
            optionFilterProp="children"
          >
            {departments.map((dept) => (
              <Select.Option key={dept.id} value={dept.id}>
                <ApartmentOutlined /> {dept.code ? `[${dept.code}] ` : ''}{dept.name}
              </Select.Option>
            ))}
          </Select>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
            New Cost Center
          </Button>
        </Space>
      }
    >
      <Table columns={columns} dataSource={filteredData} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />

      <Modal title="Create Cost Center" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} confirmLoading={saving} okText="Create" width={600}>
        <Form layout="vertical" form={form} initialValues={{ cost_center_type: 'department', is_active: true }}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input placeholder="Unique code" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item
            name="department"
            label={
              <span>
                <ApartmentOutlined /> Department (Required)
              </span>
            }
            rules={[{ required: true, message: 'Please select a department' }]}
            tooltip="Each cost center must belong to a department"
          >
            <Select
              placeholder="Select department"
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
            >
              {departments.map((dept) => (
                <Select.Option key={dept.id} value={dept.id}>
                  {dept.code ? `[${dept.code}] ` : ''}{dept.name} - {dept.company?.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="branch" label="Branch (Optional)" tooltip="Branch is auto-populated from department if applicable">
            <Select placeholder="Select branch (optional)" allowClear showSearch optionFilterProp="children">
              {branches.map((branch) => (
                <Select.Option key={branch.id} value={branch.id}>
                  {branch.code ? `[${branch.code}] ` : ''}{branch.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="cost_center_type" label="Type">
            <Select
              options={[
                { value: 'department', label: 'Department' },
                { value: 'branch', label: 'Branch' },
                { value: 'program', label: 'Program / Grant' },
                { value: 'project', label: 'Project' },
                { value: 'production_line', label: 'Production Line' },
              ]}
            />
          </Form.Item>
          <Form.Item name="default_currency" label="Default Currency">
            <Input placeholder="e.g., BDT" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default CostCenters;

