import React, { useState } from 'react';
import {
  Space,
  Button,
  Select,
  DatePicker,
  Input,
  Tag,
  Dropdown,
  Popover,
  Form,
  Row,
  Col,
  Divider,
  message,
} from 'antd';
import {
  FilterOutlined,
  SearchOutlined,
  SaveOutlined,
  DeleteOutlined,
  StarOutlined,
  StarFilled,
  DownOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

/**
 * SmartFilters - Advanced filtering component with saved filters
 * Supports quick filters, custom filters, and saved filter presets
 */
const SmartFilters = ({
  filters = [],
  quickFilters = [],
  savedFilters = [],
  onFilterChange,
  onSaveFilter,
  onDeleteFilter,
  showSearch = true,
  searchPlaceholder = 'Search...',
}) => {
  const [form] = Form.useForm();
  const [activeFilters, setActiveFilters] = useState({});
  const [searchValue, setSearchValue] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saveFilterVisible, setSaveFilterVisible] = useState(false);
  const [filterName, setFilterName] = useState('');

  // Handle filter change
  const handleFilterChange = (field, value) => {
    const newFilters = { ...activeFilters, [field]: value };

    // Remove empty filters
    Object.keys(newFilters).forEach(key => {
      if (newFilters[key] === undefined || newFilters[key] === null || newFilters[key] === '') {
        delete newFilters[key];
      }
    });

    setActiveFilters(newFilters);

    if (onFilterChange) {
      onFilterChange({ ...newFilters, search: searchValue });
    }
  };

  // Handle search
  const handleSearch = (value) => {
    setSearchValue(value);
    if (onFilterChange) {
      onFilterChange({ ...activeFilters, search: value });
    }
  };

  // Apply quick filter
  const applyQuickFilter = (filter) => {
    setActiveFilters(filter);
    form.setFieldsValue(filter);
    if (onFilterChange) {
      onFilterChange({ ...filter, search: searchValue });
    }
  };

  // Apply saved filter
  const applySavedFilter = (filter) => {
    setActiveFilters(filter.filters);
    form.setFieldsValue(filter.filters);
    if (onFilterChange) {
      onFilterChange({ ...filter.filters, search: searchValue });
    }
  };

  // Save current filter
  const handleSaveFilter = () => {
    if (!filterName) {
      message.warning('Please enter a filter name');
      return;
    }

    if (onSaveFilter) {
      onSaveFilter({
        name: filterName,
        filters: activeFilters,
      });
      message.success('Filter saved successfully');
      setSaveFilterVisible(false);
      setFilterName('');
    }
  };

  // Clear all filters
  const clearFilters = () => {
    setActiveFilters({});
    setSearchValue('');
    form.resetFields();
    if (onFilterChange) {
      onFilterChange({});
    }
  };

  // Render filter input based on type
  const renderFilterInput = (filter) => {
    switch (filter.type) {
      case 'select':
        return (
          <Select
            style={{ width: 200 }}
            placeholder={`Select ${filter.label}`}
            allowClear
            showSearch
            optionFilterProp="children"
            options={filter.options || []}
            value={activeFilters[filter.field]}
            onChange={(value) => handleFilterChange(filter.field, value)}
          />
        );

      case 'multiselect':
        return (
          <Select
            mode="multiple"
            style={{ width: 250 }}
            placeholder={`Select ${filter.label}`}
            allowClear
            showSearch
            optionFilterProp="children"
            options={filter.options || []}
            value={activeFilters[filter.field]}
            onChange={(value) => handleFilterChange(filter.field, value)}
          />
        );

      case 'daterange':
        return (
          <RangePicker
            style={{ width: 300 }}
            value={activeFilters[filter.field]}
            onChange={(dates) => handleFilterChange(filter.field, dates)}
          />
        );

      case 'date':
        return (
          <DatePicker
            style={{ width: 200 }}
            value={activeFilters[filter.field]}
            onChange={(date) => handleFilterChange(filter.field, date)}
          />
        );

      case 'number':
        return (
          <Input
            type="number"
            style={{ width: 150 }}
            placeholder={filter.placeholder || filter.label}
            value={activeFilters[filter.field]}
            onChange={(e) => handleFilterChange(filter.field, e.target.value)}
          />
        );

      default:
        return (
          <Input
            style={{ width: 200 }}
            placeholder={filter.placeholder || filter.label}
            value={activeFilters[filter.field]}
            onChange={(e) => handleFilterChange(filter.field, e.target.value)}
          />
        );
    }
  };

  // Saved filters dropdown
  const savedFiltersMenu = {
    items: savedFilters.map((filter, index) => ({
      key: index,
      label: (
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <span onClick={() => applySavedFilter(filter)}>
            <StarFilled style={{ color: '#faad14', marginRight: 8 }} />
            {filter.name}
          </span>
          {onDeleteFilter && (
            <DeleteOutlined
              style={{ color: '#ff4d4f' }}
              onClick={(e) => {
                e.stopPropagation();
                onDeleteFilter(filter.id);
              }}
            />
          )}
        </Space>
      ),
      onClick: () => applySavedFilter(filter),
    })),
  };

  const activeFilterCount = Object.keys(activeFilters).length;

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Quick Filters and Search Row */}
      <Row gutter={[8, 8]} align="middle" style={{ marginBottom: 12 }}>
        <Col flex="auto">
          <Space wrap>
            {/* Quick Filter Tags */}
            {quickFilters.map((qf, index) => (
              <Tag
                key={index}
                icon={qf.icon}
                color={qf.color || 'blue'}
                style={{ cursor: 'pointer', padding: '4px 12px' }}
                onClick={() => applyQuickFilter(qf.filter)}
              >
                {qf.label}
              </Tag>
            ))}
          </Space>
        </Col>

        {showSearch && (
          <Col>
            <Input.Search
              placeholder={searchPlaceholder}
              allowClear
              style={{ width: 300 }}
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onSearch={handleSearch}
              prefix={<SearchOutlined />}
            />
          </Col>
        )}
      </Row>

      {/* Main Filters Row */}
      <Row gutter={[8, 8]} align="middle">
        <Col flex="auto">
          <Form form={form} layout="inline">
            <Space wrap>
              {filters.map((filter, index) => (
                <Form.Item
                  key={index}
                  name={filter.field}
                  label={filter.label}
                  style={{ marginBottom: 0 }}
                >
                  {renderFilterInput(filter)}
                </Form.Item>
              ))}
            </Space>
          </Form>
        </Col>

        <Col>
          <Space>
            {/* Advanced Filters Toggle */}
            {filters.length > 4 && (
              <Button
                icon={<FilterOutlined />}
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                Advanced {showAdvanced ? '▲' : '▼'}
              </Button>
            )}

            {/* Saved Filters */}
            {savedFilters.length > 0 && (
              <Dropdown menu={savedFiltersMenu} trigger={['click']}>
                <Button icon={<StarOutlined />}>
                  Saved Filters <DownOutlined />
                </Button>
              </Dropdown>
            )}

            {/* Save Current Filter */}
            {activeFilterCount > 0 && onSaveFilter && (
              <Popover
                content={
                  <Space direction="vertical" style={{ width: 250 }}>
                    <Input
                      placeholder="Filter name"
                      value={filterName}
                      onChange={(e) => setFilterName(e.target.value)}
                      onPressEnter={handleSaveFilter}
                    />
                    <Button
                      type="primary"
                      block
                      icon={<SaveOutlined />}
                      onClick={handleSaveFilter}
                    >
                      Save Filter
                    </Button>
                  </Space>
                }
                title="Save Current Filter"
                trigger="click"
                open={saveFilterVisible}
                onOpenChange={setSaveFilterVisible}
              >
                <Button icon={<SaveOutlined />}>Save</Button>
              </Popover>
            )}

            {/* Clear Filters */}
            {activeFilterCount > 0 && (
              <Button onClick={clearFilters}>
                Clear ({activeFilterCount})
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      {/* Advanced Filters Section */}
      {showAdvanced && filters.length > 4 && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <Row gutter={[16, 16]}>
            {filters.slice(4).map((filter, index) => (
              <Col key={index} span={6}>
                <Form.Item label={filter.label} style={{ marginBottom: 0 }}>
                  {renderFilterInput(filter)}
                </Form.Item>
              </Col>
            ))}
          </Row>
        </>
      )}
    </div>
  );
};

export default SmartFilters;
