import React, { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  companyGroupService,
  companyService,
  branchService,
  departmentService,
  organizationalContextService,
  organizationHelpers,
} from '../../services/organization';

const OrganizationalContextSelector = ({
  onContextChange,
  showAllLevels = true,
  compact = false,
  className = ''
}) => {
  // State for dropdown options
  const [companyGroups, setCompanyGroups] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [branches, setBranches] = useState([]);
  const [departments, setDepartments] = useState([]);

  // State for selected values
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedBranch, setSelectedBranch] = useState(null);
  const [selectedDepartment, setSelectedDepartment] = useState(null);

  // Loading states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check if company requires branches
  const requiresBranches = useMemo(() => {
    return organizationHelpers.requiresBranchStructure(selectedCompany);
  }, [selectedCompany]);

  // Load initial data and current context
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load company groups
        const groupsResponse = await companyGroupService.listMinimal();
        setCompanyGroups(groupsResponse.data || []);

        // Try to load current context
        try {
          const contextResponse = await organizationalContextService.getCurrent();
          const context = contextResponse.data;

          if (context.company_group) {
            setSelectedGroup(context.company_group);
            await loadCompaniesForGroup(context.company_group.id);
          }

          if (context.company) {
            setSelectedCompany(context.company);
            if (context.company.requires_branch_structure) {
              await loadBranchesForCompany(context.company.id);
            }
            await loadDepartmentsForCompany(context.company.id);
          }

          if (context.branch) {
            setSelectedBranch(context.branch);
          }

          if (context.department) {
            setSelectedDepartment(context.department);
          }
        } catch (contextErr) {
          console.warn('No existing context found');
        }
      } catch (err) {
        console.error('Failed to load organizational data:', err);
        setError('Failed to load organizational data');
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  // Load companies for selected group
  const loadCompaniesForGroup = async (groupId) => {
    try {
      const response = await companyGroupService.getCompanies(groupId);
      setCompanies(response.data || []);
    } catch (err) {
      console.error('Failed to load companies:', err);
    }
  };

  // Load branches for selected company
  const loadBranchesForCompany = async (companyId) => {
    try {
      const response = await companyService.getBranches(companyId);
      setBranches(response.data || []);
    } catch (err) {
      console.error('Failed to load branches:', err);
    }
  };

  // Load departments for selected company or branch
  const loadDepartmentsForCompany = async (companyId, branchId = null) => {
    try {
      const params = branchId ? { branch: branchId } : { company: companyId };
      const response = await departmentService.list(params);
      setDepartments(response.data.results || response.data || []);
    } catch (err) {
      console.error('Failed to load departments:', err);
    }
  };

  // Handle group change
  const handleGroupChange = async (e) => {
    const groupId = e.target.value;
    const group = companyGroups.find(g => String(g.id) === String(groupId));

    setSelectedGroup(group || null);
    setSelectedCompany(null);
    setSelectedBranch(null);
    setSelectedDepartment(null);
    setCompanies([]);
    setBranches([]);
    setDepartments([]);

    if (groupId) {
      await loadCompaniesForGroup(groupId);
    }

    notifyContextChange(group, null, null, null);
  };

  // Handle company change
  const handleCompanyChange = async (e) => {
    const companyId = e.target.value;
    const company = companies.find(c => String(c.id) === String(companyId));

    setSelectedCompany(company || null);
    setSelectedBranch(null);
    setSelectedDepartment(null);
    setBranches([]);
    setDepartments([]);

    if (company) {
      if (company.requires_branch_structure) {
        await loadBranchesForCompany(company.id);
      }
      await loadDepartmentsForCompany(company.id);
    }

    notifyContextChange(selectedGroup, company, null, null);
  };

  // Handle branch change
  const handleBranchChange = async (e) => {
    const branchId = e.target.value;
    const branch = branches.find(b => String(b.id) === String(branchId));

    setSelectedBranch(branch || null);
    setSelectedDepartment(null);
    setDepartments([]);

    if (branch && selectedCompany) {
      await loadDepartmentsForCompany(selectedCompany.id, branch.id);
    }

    notifyContextChange(selectedGroup, selectedCompany, branch, null);
  };

  // Handle department change
  const handleDepartmentChange = (e) => {
    const deptId = e.target.value;
    const dept = departments.find(d => String(d.id) === String(deptId));

    setSelectedDepartment(dept || null);
    notifyContextChange(selectedGroup, selectedCompany, selectedBranch, dept);
  };

  // Notify parent component and backend
  const notifyContextChange = async (group, company, branch, department) => {
    const context = {
      company_group_id: group?.id || null,
      company_id: company?.id || null,
      branch_id: branch?.id || null,
      department_id: department?.id || null,
    };

    // Update backend context
    try {
      await organizationalContextService.updateContext(context);
    } catch (err) {
      console.error('Failed to update organizational context:', err);
    }

    // Notify parent component
    if (onContextChange) {
      onContextChange({ group, company, branch, department });
    }

    // Update localStorage for API interceptor
    if (company?.id) {
      localStorage.setItem('twist-active-company', String(company.id));
    }
    if (branch?.id) {
      localStorage.setItem('twist-active-branch', String(branch.id));
    }
    if (department?.id) {
      localStorage.setItem('twist-active-department', String(department.id));
    }
  };

  // Build hierarchy display
  const hierarchyDisplay = useMemo(() => {
    return organizationHelpers.buildHierarchyDisplay(
      selectedGroup,
      selectedCompany,
      selectedBranch,
      selectedDepartment
    );
  }, [selectedGroup, selectedCompany, selectedBranch, selectedDepartment]);

  if (loading && !companyGroups.length) {
    return <div className="text-sm text-gray-500">Loading organizational data...</div>;
  }

  if (error) {
    return <div className="text-sm text-red-500">{error}</div>;
  }

  // Compact view: Show single dropdown with hierarchy display
  if (compact) {
    return (
      <div className={`organizational-context-compact ${className}`}>
        <div className="text-sm font-medium text-gray-700">
          {hierarchyDisplay || 'No organization selected'}
        </div>
      </div>
    );
  }

  // Full view: Show all dropdown levels
  return (
    <div className={`organizational-context-selector ${className}`}>
      <div className="space-y-3">
        {/* Company Group Selector */}
        {showAllLevels && (
          <div>
            <label htmlFor="company-group" className="block text-sm font-medium text-gray-700 mb-1">
              Company Group
            </label>
            <select
              id="company-group"
              value={selectedGroup?.id || ''}
              onChange={handleGroupChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select Company Group</option>
              {companyGroups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.code ? `[${group.code}] ` : ''}{group.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Company Selector */}
        <div>
          <label htmlFor="company" className="block text-sm font-medium text-gray-700 mb-1">
            Company *
          </label>
          <select
            id="company"
            value={selectedCompany?.id || ''}
            onChange={handleCompanyChange}
            disabled={showAllLevels && !selectedGroup}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            <option value="">Select Company</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.code ? `[${company.code}] ` : ''}{company.name}
              </option>
            ))}
          </select>
        </div>

        {/* Branch Selector (only if company requires it) */}
        {requiresBranches && (
          <div>
            <label htmlFor="branch" className="block text-sm font-medium text-gray-700 mb-1">
              Branch
            </label>
            <select
              id="branch"
              value={selectedBranch?.id || ''}
              onChange={handleBranchChange}
              disabled={!selectedCompany}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="">Select Branch</option>
              {branches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.code ? `[${branch.code}] ` : ''}{branch.name} - {organizationHelpers.formatBranchLocation(branch)}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Department Selector */}
        {showAllLevels && (
          <div>
            <label htmlFor="department" className="block text-sm font-medium text-gray-700 mb-1">
              Department
            </label>
            <select
              id="department"
              value={selectedDepartment?.id || ''}
              onChange={handleDepartmentChange}
              disabled={!selectedCompany}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="">Select Department</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.code ? `[${dept.code}] ` : ''}{dept.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Current Selection Display */}
        {hierarchyDisplay && (
          <div className="mt-4 pt-3 border-t border-gray-200">
            <div className="text-xs text-gray-500 mb-1">Current Context:</div>
            <div className="text-sm font-medium text-gray-900">{hierarchyDisplay}</div>
          </div>
        )}
      </div>
    </div>
  );
};

OrganizationalContextSelector.propTypes = {
  onContextChange: PropTypes.func,
  showAllLevels: PropTypes.bool,
  compact: PropTypes.bool,
  className: PropTypes.string,
};

export default OrganizationalContextSelector;
