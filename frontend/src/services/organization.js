import api from './api';

// ==================== Company Groups ====================

export const companyGroupService = {
  // List all company groups
  list: (params = {}) => api.get('/companies/groups/', { params }),

  // Get minimal list (id, code, name only)
  listMinimal: () => api.get('/companies/groups/minimal/'),

  // Get a single company group
  get: (id) => api.get(`/companies/groups/${id}/`),

  // Create a new company group
  create: (data) => api.post('/companies/groups/', data),

  // Update a company group
  update: (id, data) => api.put(`/companies/groups/${id}/`, data),

  // Partial update a company group
  patch: (id, data) => api.patch(`/companies/groups/${id}/`, data),

  // Delete a company group
  delete: (id) => api.delete(`/companies/groups/${id}/`),

  // Get companies under a group
  getCompanies: (id) => api.get(`/companies/groups/${id}/companies/`),

  // Get child groups under a group
  getChildGroups: (id) => api.get(`/companies/groups/${id}/child-groups/`),
};

// ==================== Companies ====================

export const companyService = {
  // List all companies
  list: (params = {}) => api.get('/companies/companies/', { params }),

  // Get minimal list (id, code, name only)
  listMinimal: () => api.get('/companies/companies/minimal/'),

  // Get a single company
  get: (id) => api.get(`/companies/companies/${id}/`),

  // Create a new company
  create: (data) => api.post('/companies/companies/', data),

  // Update a company
  update: (id, data) => api.put(`/companies/companies/${id}/`, data),

  // Partial update a company
  patch: (id, data) => api.patch(`/companies/companies/${id}/`, data),

  // Delete a company
  delete: (id) => api.delete(`/companies/companies/${id}/`),

  // Get branches under a company
  getBranches: (id) => api.get(`/companies/companies/${id}/branches/`),

  // Get departments under a company
  getDepartments: (id) => api.get(`/companies/companies/${id}/departments/`),

  // Get subsidiary companies
  getSubsidiaries: (id) => api.get(`/companies/companies/${id}/subsidiaries/`),

  // Get fiscal year info
  getFiscalYear: (id) => api.get(`/companies/companies/${id}/fiscal-year/`),
};

// ==================== Branches ====================

export const branchService = {
  // List all branches
  list: (params = {}) => api.get('/companies/branches/', { params }),

  // Get minimal list (id, code, name only)
  listMinimal: () => api.get('/companies/branches/minimal/'),

  // Get a single branch
  get: (id) => api.get(`/companies/branches/${id}/`),

  // Create a new branch
  create: (data) => api.post('/companies/branches/', data),

  // Update a branch
  update: (id, data) => api.put(`/companies/branches/${id}/`, data),

  // Partial update a branch
  patch: (id, data) => api.patch(`/companies/branches/${id}/`, data),

  // Delete a branch
  delete: (id) => api.delete(`/companies/branches/${id}/`),

  // Get departments under a branch
  getDepartments: (id) => api.get(`/companies/branches/${id}/departments/`),

  // Get sub-branches
  getSubBranches: (id) => api.get(`/companies/branches/${id}/sub-branches/`),
};

// ==================== Departments ====================

export const departmentService = {
  // List all departments
  list: (params = {}) => api.get('/companies/departments/', { params }),

  // Get minimal list (id, code, name only)
  listMinimal: () => api.get('/companies/departments/minimal/'),

  // Get a single department
  get: (id) => api.get(`/companies/departments/${id}/`),

  // Create a new department
  create: (data) => api.post('/companies/departments/', data),

  // Update a department
  update: (id, data) => api.put(`/companies/departments/${id}/`, data),

  // Partial update a department
  patch: (id, data) => api.patch(`/companies/departments/${id}/`, data),

  // Delete a department
  delete: (id) => api.delete(`/companies/departments/${id}/`),

  // Get members of a department
  getMembers: (id) => api.get(`/companies/departments/${id}/members/`),

  // Get sub-departments
  getSubDepartments: (id) => api.get(`/companies/departments/${id}/sub-departments/`),
};

// ==================== Department Membership ====================

export const departmentMembershipService = {
  // List all department memberships
  list: (params = {}) => api.get('/companies/department-memberships/', { params }),

  // Get a single department membership
  get: (id) => api.get(`/companies/department-memberships/${id}/`),

  // Create a new department membership
  create: (data) => api.post('/companies/department-memberships/', data),

  // Update a department membership
  update: (id, data) => api.put(`/companies/department-memberships/${id}/`, data),

  // Partial update a department membership
  patch: (id, data) => api.patch(`/companies/department-memberships/${id}/`, data),

  // Delete a department membership
  delete: (id) => api.delete(`/companies/department-memberships/${id}/`),

  // Get memberships by department
  byDepartment: (departmentId) => api.get('/companies/department-memberships/', {
    params: { department: departmentId }
  }),

  // Get memberships by user
  byUser: (userId) => api.get('/companies/department-memberships/', {
    params: { user: userId }
  }),
};

// ==================== Organizational Context ====================

export const organizationalContextService = {
  // Get current organizational context
  getCurrent: () => api.get('/companies/context/'),

  // Update organizational context (set active group/company/branch/department)
  updateContext: (data) => api.post('/companies/context/', data),
};

// ==================== User Organizational Access ====================

export const userOrganizationalAccessService = {
  // Get user's organizational access
  getUserAccess: (userId) => api.get(`/users/${userId}/organizational-access/`),

  // Update user's organizational access
  updateUserAccess: (userId, data) => api.put(`/users/${userId}/organizational-access/`, data),

  // Get current user's organizational access
  getMyAccess: () => api.get('/users/me/organizational-access/'),

  // Update current user's organizational access
  updateMyAccess: (data) => api.put('/users/me/organizational-access/', data),
};

// ==================== Helper Functions ====================

export const organizationHelpers = {
  /**
   * Build hierarchy path display (e.g., "Group > Company > Branch > Department")
   */
  buildHierarchyDisplay: (group, company, branch, department) => {
    const parts = [];
    if (group?.name) parts.push(group.name);
    if (company?.name) parts.push(company.name);
    if (branch?.name) parts.push(branch.name);
    if (department?.name) parts.push(department.name);
    return parts.join(' > ');
  },

  /**
   * Format location display for branches
   */
  formatBranchLocation: (branch) => {
    const parts = [];
    if (branch.city) parts.push(branch.city);
    if (branch.state_province) parts.push(branch.state_province);
    if (branch.country) parts.push(branch.country);
    return parts.join(', ') || 'No location specified';
  },

  /**
   * Get branch type label
   */
  getBranchTypeLabel: (branchType) => {
    const types = {
      'headquarters': 'Headquarters',
      'factory': 'Factory/Manufacturing',
      'warehouse': 'Warehouse',
      'retail': 'Retail Store',
      'office': 'Office',
      'regional': 'Regional Office',
      'distribution': 'Distribution Center',
      'other': 'Other'
    };
    return types[branchType] || branchType;
  },

  /**
   * Get department type label
   */
  getDepartmentTypeLabel: (deptType) => {
    const types = {
      'operational': 'Operational',
      'administrative': 'Administrative',
      'functional': 'Functional',
      'project': 'Project-Based',
      'program': 'Program/Initiative',
      'cost_center': 'Cost Center',
      'other': 'Other'
    };
    return types[deptType] || deptType;
  },

  /**
   * Get membership role label
   */
  getMembershipRoleLabel: (role) => {
    const roles = {
      'head': 'Head',
      'deputy_head': 'Deputy Head',
      'manager': 'Manager',
      'staff': 'Staff',
      'intern': 'Intern',
      'contractor': 'Contractor',
      'consultant': 'Consultant',
      'volunteer': 'Volunteer'
    };
    return roles[role] || role;
  },

  /**
   * Check if company requires branch structure
   */
  requiresBranchStructure: (company) => {
    return company?.requires_branch_structure === true;
  },
};

// Default export with all services
export default {
  companyGroup: companyGroupService,
  company: companyService,
  branch: branchService,
  department: departmentService,
  departmentMembership: departmentMembershipService,
  context: organizationalContextService,
  userAccess: userOrganizationalAccessService,
  helpers: organizationHelpers,
};
