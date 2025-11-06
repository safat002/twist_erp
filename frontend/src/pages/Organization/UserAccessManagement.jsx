import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Transfer,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Tag,
  Descriptions,
  Tabs,
  Table,
  Avatar,
  Divider,
  Row,
  Col,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UserOutlined,
  TeamOutlined,
  BankOutlined,
  ShopOutlined,
  ApartmentOutlined,
  CheckCircleOutlined,
  StarFilled,
} from '@ant-design/icons';
import {
  companyGroupService,
  companyService,
  branchService,
  departmentService,
  userOrganizationalAccessService,
  organizationHelpers,
} from '../../services/organization';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const UserAccessManagement = () => {
  // State for all organizational entities
  const [users, setUsers] = useState([]);
  const [companyGroups, setCompanyGroups] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [branches, setBranches] = useState([]);
  const [departments, setDepartments] = useState([]);

  // Selected user and their access
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userAccess, setUserAccess] = useState(null);

  // Transfer list states
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [selectedCompanies, setSelectedCompanies] = useState([]);
  const [selectedBranches, setSelectedBranches] = useState([]);
  const [selectedDepartments, setSelectedDepartments] = useState([]);

  // Primary selections
  const [primaryGroup, setPrimaryGroup] = useState(null);
  const [primaryCompany, setPrimaryCompany] = useState(null);
  const [primaryBranch, setPrimaryBranch] = useState(null);
  const [primaryDepartment, setPrimaryDepartment] = useState(null);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedUserId) {
      loadUserAccess(selectedUserId);
    }
  }, [selectedUserId]);

  const loadInitialData = async () => {
    try {
      setLoading(true);

      // Load all organizational entities
      const [groupsRes, companiesRes, branchesRes, deptsRes] = await Promise.all([
        companyGroupService.list(),
        companyService.list(),
        branchService.list(),
        departmentService.list(),
      ]);

      setCompanyGroups(groupsRes.data.results || groupsRes.data || []);
      setCompanies(companiesRes.data.results || companiesRes.data || []);
      setBranches(branchesRes.data.results || branchesRes.data || []);
      setDepartments(deptsRes.data.results || deptsRes.data || []);

      // TODO: Load users from your users API
      // For now, using mock data
      setUsers([
        { id: 1, username: 'admin', email: 'admin@company.com', full_name: 'Admin User' },
        { id: 2, username: 'manager', email: 'manager@company.com', full_name: 'Manager User' },
      ]);
    } catch (error) {
      message.error('Failed to load organizational data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadUserAccess = async (userId) => {
    try {
      setLoading(true);
      const user = users.find((u) => u.id === userId);
      setSelectedUser(user);

      // Load user's organizational access
      const response = await userOrganizationalAccessService.getUserAccess(userId);
      const access = response.data;
      setUserAccess(access);

      // Set selected IDs for transfer lists
      setSelectedGroups(access.access_groups?.map((g) => g.id) || []);
      setSelectedCompanies(access.access_companies?.map((c) => c.id) || []);
      setSelectedBranches(access.access_branches?.map((b) => b.id) || []);
      setSelectedDepartments(access.access_departments?.map((d) => d.id) || []);

      // Set primary selections
      setPrimaryGroup(access.primary_group?.id || null);
      setPrimaryCompany(access.primary_company?.id || null);
      setPrimaryBranch(access.primary_branch?.id || null);
      setPrimaryDepartment(access.primary_department?.id || null);
    } catch (error) {
      console.error('Failed to load user access:', error);
      // Initialize empty access if not found
      setUserAccess({});
      setSelectedGroups([]);
      setSelectedCompanies([]);
      setSelectedBranches([]);
      setSelectedDepartments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAccess = async () => {
    try {
      setSaving(true);

      const accessData = {
        access_groups: selectedGroups,
        access_companies: selectedCompanies,
        access_branches: selectedBranches,
        access_departments: selectedDepartments,
        primary_group: primaryGroup,
        primary_company: primaryCompany,
        primary_branch: primaryBranch,
        primary_department: primaryDepartment,
      };

      await userOrganizationalAccessService.updateUserAccess(selectedUserId, accessData);
      message.success('User access updated successfully');
      loadUserAccess(selectedUserId);
    } catch (error) {
      message.error('Failed to update user access');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  // Users table columns
  const userColumns = [
    {
      title: 'User',
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div><strong>{record.full_name || record.username}</strong></div>
            <div><Text type="secondary" style={{ fontSize: 12 }}>{record.email}</Text></div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        <Button
          type={selectedUserId === record.id ? 'primary' : 'default'}
          onClick={() => setSelectedUserId(record.id)}
          icon={<TeamOutlined />}
        >
          {selectedUserId === record.id ? 'Selected' : 'Manage Access'}
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <TeamOutlined /> User Access Management
      </Title>
      <Text type="secondary">
        Assign organizational access to users across company groups, companies, branches, and departments
      </Text>

      <Row gutter={24} style={{ marginTop: 24 }}>
        {/* Left Panel - User Selection */}
        <Col span={10}>
          <Card title="Select User" loading={loading}>
            <Table
              columns={userColumns}
              dataSource={users}
              rowKey="id"
              size="small"
              pagination={false}
              rowClassName={(record) => (selectedUserId === record.id ? 'ant-table-row-selected' : '')}
            />
          </Card>
        </Col>

        {/* Right Panel - Access Configuration */}
        <Col span={14}>
          {selectedUser ? (
            <Card
              title={
                <Space>
                  <Avatar icon={<UserOutlined />} />
                  <span>Access Configuration for {selectedUser.full_name || selectedUser.username}</span>
                </Space>
              }
              loading={loading}
              extra={
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={handleSaveAccess}
                  loading={saving}
                >
                  Save Access
                </Button>
              }
            >
              <Tabs defaultActiveKey="1">
                {/* Company Groups Tab */}
                <TabPane
                  tab={
                    <span>
                      <BankOutlined />
                      Company Groups <Badge count={selectedGroups.length} style={{ marginLeft: 8 }} />
                    </span>
                  }
                  key="1"
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <Text strong>Accessible Company Groups</Text>
                      <p style={{ marginTop: 8, color: '#666' }}>
                        Select which company groups this user can access
                      </p>
                      <Transfer
                        dataSource={companyGroups.map((g) => ({
                          key: g.id,
                          title: `${g.code ? `[${g.code}] ` : ''}${g.name}`,
                          description: g.group_type,
                        }))}
                        titles={['Available', 'Accessible']}
                        targetKeys={selectedGroups}
                        onChange={setSelectedGroups}
                        render={(item) => (
                          <div>
                            <div>{item.title}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>{item.description}</div>
                          </div>
                        )}
                        showSearch
                        listStyle={{ width: 250, height: 300 }}
                      />
                    </div>

                    <Divider />

                    <div>
                      <Text strong>
                        <StarFilled style={{ color: '#faad14' }} /> Primary Group (Default on Login)
                      </Text>
                      <Select
                        style={{ width: '100%', marginTop: 8 }}
                        placeholder="Select primary company group"
                        value={primaryGroup}
                        onChange={setPrimaryGroup}
                        allowClear
                      >
                        {companyGroups
                          .filter((g) => selectedGroups.includes(g.id))
                          .map((g) => (
                            <Select.Option key={g.id} value={g.id}>
                              {g.code ? `[${g.code}] ` : ''}{g.name}
                            </Select.Option>
                          ))}
                      </Select>
                    </div>
                  </Space>
                </TabPane>

                {/* Companies Tab */}
                <TabPane
                  tab={
                    <span>
                      <BankOutlined />
                      Companies <Badge count={selectedCompanies.length} style={{ marginLeft: 8 }} />
                    </span>
                  }
                  key="2"
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <Text strong>Accessible Companies</Text>
                      <p style={{ marginTop: 8, color: '#666' }}>
                        Select which companies this user can access
                      </p>
                      <Transfer
                        dataSource={companies.map((c) => ({
                          key: c.id,
                          title: `${c.code ? `[${c.code}] ` : ''}${c.name}`,
                          description: c.company_group?.name || 'No group',
                        }))}
                        titles={['Available', 'Accessible']}
                        targetKeys={selectedCompanies}
                        onChange={setSelectedCompanies}
                        render={(item) => (
                          <div>
                            <div>{item.title}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>{item.description}</div>
                          </div>
                        )}
                        showSearch
                        listStyle={{ width: 250, height: 300 }}
                      />
                    </div>

                    <Divider />

                    <div>
                      <Text strong>
                        <StarFilled style={{ color: '#faad14' }} /> Primary Company (Default on Login)
                      </Text>
                      <Select
                        style={{ width: '100%', marginTop: 8 }}
                        placeholder="Select primary company"
                        value={primaryCompany}
                        onChange={setPrimaryCompany}
                        allowClear
                      >
                        {companies
                          .filter((c) => selectedCompanies.includes(c.id))
                          .map((c) => (
                            <Select.Option key={c.id} value={c.id}>
                              {c.code ? `[${c.code}] ` : ''}{c.name}
                            </Select.Option>
                          ))}
                      </Select>
                    </div>
                  </Space>
                </TabPane>

                {/* Branches Tab */}
                <TabPane
                  tab={
                    <span>
                      <ShopOutlined />
                      Branches <Badge count={selectedBranches.length} style={{ marginLeft: 8 }} />
                    </span>
                  }
                  key="3"
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <Text strong>Accessible Branches</Text>
                      <p style={{ marginTop: 8, color: '#666' }}>
                        Select which branches this user can access
                      </p>
                      <Transfer
                        dataSource={branches.map((b) => ({
                          key: b.id,
                          title: `${b.code ? `[${b.code}] ` : ''}${b.name}`,
                          description: `${b.company?.name} - ${organizationHelpers.formatBranchLocation(b)}`,
                        }))}
                        titles={['Available', 'Accessible']}
                        targetKeys={selectedBranches}
                        onChange={setSelectedBranches}
                        render={(item) => (
                          <div>
                            <div>{item.title}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>{item.description}</div>
                          </div>
                        )}
                        showSearch
                        listStyle={{ width: 250, height: 300 }}
                      />
                    </div>

                    <Divider />

                    <div>
                      <Text strong>
                        <StarFilled style={{ color: '#faad14' }} /> Primary Branch (Default on Login)
                      </Text>
                      <Select
                        style={{ width: '100%', marginTop: 8 }}
                        placeholder="Select primary branch"
                        value={primaryBranch}
                        onChange={setPrimaryBranch}
                        allowClear
                      >
                        {branches
                          .filter((b) => selectedBranches.includes(b.id))
                          .map((b) => (
                            <Select.Option key={b.id} value={b.id}>
                              {b.code ? `[${b.code}] ` : ''}{b.name} - {organizationHelpers.formatBranchLocation(b)}
                            </Select.Option>
                          ))}
                      </Select>
                    </div>
                  </Space>
                </TabPane>

                {/* Departments Tab */}
                <TabPane
                  tab={
                    <span>
                      <ApartmentOutlined />
                      Departments <Badge count={selectedDepartments.length} style={{ marginLeft: 8 }} />
                    </span>
                  }
                  key="4"
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <Text strong>Accessible Departments</Text>
                      <p style={{ marginTop: 8, color: '#666' }}>
                        Select which departments this user can access
                      </p>
                      <Transfer
                        dataSource={departments.map((d) => ({
                          key: d.id,
                          title: `${d.code ? `[${d.code}] ` : ''}${d.name}`,
                          description: `${d.company?.name}${d.branch ? ` - ${d.branch.name}` : ''}`,
                        }))}
                        titles={['Available', 'Accessible']}
                        targetKeys={selectedDepartments}
                        onChange={setSelectedDepartments}
                        render={(item) => (
                          <div>
                            <div>{item.title}</div>
                            <div style={{ fontSize: 12, color: '#999' }}>{item.description}</div>
                          </div>
                        )}
                        showSearch
                        listStyle={{ width: 250, height: 300 }}
                      />
                    </div>

                    <Divider />

                    <div>
                      <Text strong>
                        <StarFilled style={{ color: '#faad14' }} /> Primary Department (Default on Login)
                      </Text>
                      <Select
                        style={{ width: '100%', marginTop: 8 }}
                        placeholder="Select primary department"
                        value={primaryDepartment}
                        onChange={setPrimaryDepartment}
                        allowClear
                      >
                        {departments
                          .filter((d) => selectedDepartments.includes(d.id))
                          .map((d) => (
                            <Select.Option key={d.id} value={d.id}>
                              {d.code ? `[${d.code}] ` : ''}{d.name}
                            </Select.Option>
                          ))}
                      </Select>
                    </div>
                  </Space>
                </TabPane>

                {/* Summary Tab */}
                <TabPane tab={<span><CheckCircleOutlined /> Summary</span>} key="5">
                  <Descriptions bordered column={1}>
                    <Descriptions.Item label="User">
                      <Space>
                        <Avatar icon={<UserOutlined />} />
                        {selectedUser.full_name || selectedUser.username}
                      </Space>
                    </Descriptions.Item>
                    <Descriptions.Item label="Email">{selectedUser.email}</Descriptions.Item>
                    <Descriptions.Item label="Company Groups Access">
                      <Badge count={selectedGroups.length} style={{ marginRight: 8 }} />
                      {selectedGroups.length} groups
                    </Descriptions.Item>
                    <Descriptions.Item label="Companies Access">
                      <Badge count={selectedCompanies.length} style={{ marginRight: 8 }} />
                      {selectedCompanies.length} companies
                    </Descriptions.Item>
                    <Descriptions.Item label="Branches Access">
                      <Badge count={selectedBranches.length} style={{ marginRight: 8 }} />
                      {selectedBranches.length} branches
                    </Descriptions.Item>
                    <Descriptions.Item label="Departments Access">
                      <Badge count={selectedDepartments.length} style={{ marginRight: 8 }} />
                      {selectedDepartments.length} departments
                    </Descriptions.Item>
                    <Descriptions.Item label="Primary Context">
                      {organizationHelpers.buildHierarchyDisplay(
                        companyGroups.find((g) => g.id === primaryGroup),
                        companies.find((c) => c.id === primaryCompany),
                        branches.find((b) => b.id === primaryBranch),
                        departments.find((d) => d.id === primaryDepartment)
                      ) || 'Not set'}
                    </Descriptions.Item>
                  </Descriptions>

                  <div style={{ marginTop: 24, textAlign: 'center' }}>
                    <Button
                      type="primary"
                      size="large"
                      icon={<CheckCircleOutlined />}
                      onClick={handleSaveAccess}
                      loading={saving}
                    >
                      Save All Access Changes
                    </Button>
                  </div>
                </TabPane>
              </Tabs>
            </Card>
          ) : (
            <Card>
              <div style={{ textAlign: 'center', padding: 48 }}>
                <UserOutlined style={{ fontSize: 64, color: '#ccc' }} />
                <p style={{ marginTop: 16, color: '#999' }}>
                  Select a user from the left panel to manage their organizational access
                </p>
              </div>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default UserAccessManagement;
