# Inventory Module UI/UX Implementation Guide

## Overview

This document describes the new UI/UX architecture implemented for the inventory module. The implementation provides a modern, flexible, and user-friendly interface that can accommodate all existing and future functionality.

## Architecture

### Component Library Structure

```
frontend/src/components/Inventory/
├── InventoryLayout.jsx          # Unified page layout wrapper
├── SmartFilters.jsx             # Advanced filtering component
├── InventoryStats.jsx           # KPI cards display
├── WorkflowBoard.jsx            # Kanban-style workflow board
├── CommandPalette.jsx           # Quick action palette (Ctrl+K)
├── ViewToggle.jsx               # View mode switcher
└── index.js                     # Component exports
```

## Navigation Structure

The inventory module navigation has been restructured into logical groupings:

```
Inventory
├── Dashboard
├── Master Data
│   ├── Items & Products
│   └── Warehouses & Bins
├── Inbound Operations
│   ├── Goods Receipts (GRN)
│   ├── Landed Cost Vouchers
│   └── Return To Vendor
├── Outbound Operations
│   ├── Material Issues
│   └── Requisitions
├── Stock Movements
├── Valuation & Finance
│   ├── Valuation Settings
│   ├── Cost Layers
│   ├── Valuation Report
│   └── Landed Cost Adjustment
└── Quality & Compliance
    ├── Quality Inspections
    └── Stock Holds
```

## Core Components

### 1. InventoryLayout

**Purpose**: Provides a consistent layout wrapper for all inventory pages.

**Features**:
- Unified page header with icon and title
- Breadcrumb navigation
- Action buttons area
- Flexible content area
- Optional subtitle and extra content

**Usage**:
```jsx
import { InventoryLayout } from '../../../components/Inventory';

<InventoryLayout
  title="Goods Receipts (GRN)"
  icon={<InboxOutlined />}
  subtitle="Receive and manage incoming inventory"
  breadcrumb={[
    { label: 'Inventory', path: '/inventory' },
    { label: 'Inbound Operations' },
    { label: 'Goods Receipts' },
  ]}
  actions={[
    <Button key="refresh" icon={<ReloadOutlined />} onClick={refresh}>
      Refresh
    </Button>,
    <Button key="create" type="primary" icon={<PlusOutlined />}>
      New GRN
    </Button>,
  ]}
>
  {/* Page content here */}
</InventoryLayout>
```

### 2. SmartFilters

**Purpose**: Advanced filtering system with saved filters and quick filters.

**Features**:
- Multiple filter types (select, multiselect, daterange, number, text)
- Quick filter tags
- Saved filter presets
- Search integration
- Advanced filters panel
- Filter persistence

**Usage**:
```jsx
import { SmartFilters } from '../../../components/Inventory';

<SmartFilters
  filters={[
    {
      type: 'select',
      field: 'status',
      label: 'Status',
      options: [
        { label: 'Draft', value: 'DRAFT' },
        { label: 'Approved', value: 'APPROVED' },
      ],
    },
    {
      type: 'daterange',
      field: 'date_range',
      label: 'Date Range',
    },
  ]}
  quickFilters={[
    {
      label: 'Today',
      icon: <InboxOutlined />,
      color: 'blue',
      filter: { date: 'today' },
    },
  ]}
  savedFilters={userSavedFilters}
  onFilterChange={handleFilterChange}
  onSaveFilter={handleSaveFilter}
  onDeleteFilter={handleDeleteFilter}
  searchPlaceholder="Search GRNs..."
/>
```

### 3. InventoryStats

**Purpose**: Display KPI cards with trends, progress bars, and interactions.

**Features**:
- Clickable stat cards
- Trend indicators with customizable direction
- Progress bars
- Icons and color coding
- Highlight borders
- Footer text
- Tooltips

**Usage**:
```jsx
import { InventoryStats } from '../../../components/Inventory';

<InventoryStats
  stats={[
    {
      key: 'total',
      title: 'Total GRNs',
      value: 1234,
      icon: <InboxOutlined />,
      iconColor: '#1890ff',
      trend: 5,
      trendLabel: 'vs last month',
      onClick: () => handleClick(),
    },
    {
      key: 'pending',
      title: 'Pending QC',
      value: 23,
      icon: <SafetyCertificateOutlined />,
      status: 'warning',
      progress: 75,
      progressLabel: '75% of target',
      highlight: true,
      highlightColor: '#faad14',
    },
  ]}
  loading={loading}
/>
```

### 4. WorkflowBoard

**Purpose**: Kanban-style workflow visualization with drag-and-drop.

**Features**:
- Drag and drop cards between columns
- Customizable column colors
- Card metadata display
- Empty state handling
- Custom card rendering

**Usage**:
```jsx
import { WorkflowBoard } from '../../../components/Inventory';

<WorkflowBoard
  columns={[
    {
      id: 'pending_qc',
      title: 'Pending QC',
      description: 'Awaiting inspection',
      itemIds: ['grn-1', 'grn-2'],
      headerColor: '#fff7e6',
      badgeColor: '#faad14',
      statusColor: '#faad14',
    },
  ]}
  items={{
    'grn-1': {
      id: 'grn-1',
      code: 'GRN-001',
      name: 'Supplier ABC',
      description: 'PO: PO-123',
      assignee: 'John Doe',
      dueDate: '12 Nov',
      count: 5,
      tags: ['Warehouse A'],
    },
  }}
  onDragEnd={handleDragEnd}
  renderItem={customRenderFunction} // Optional
/>
```

### 5. CommandPalette

**Purpose**: Quick action/navigation interface (Ctrl+K or Cmd+K).

**Features**:
- Keyboard navigation (Arrow keys, Enter, Escape)
- Search filtering
- Command categories
- Icon and description display
- Keyboard shortcuts display

**Integration**:
Already integrated in MainLayout. Press **Ctrl+K** or **Cmd+K** to open.

**Custom Commands**:
```jsx
import { CommandPalette } from '../../../components/Inventory';

<CommandPalette
  visible={visible}
  onClose={handleClose}
  commands={[
    {
      id: 'custom-action',
      title: 'Custom Action',
      description: 'Description of the action',
      icon: <IconComponent />,
      category: 'Action',
      keywords: ['search', 'terms'],
      action: () => doSomething(),
      shortcut: 'Ctrl+Shift+A',
    },
  ]}
/>
```

### 6. ViewToggle

**Purpose**: Switch between different view modes (Table, Cards, Kanban, etc.).

**Features**:
- Segmented control UI
- Icon + label display
- Customizable views

**Usage**:
```jsx
import { ViewToggle } from '../../../components/Inventory';

<ViewToggle
  value={viewMode}
  onChange={setViewMode}
  views={['table', 'kanban', 'cards']}
  size="middle"
/>
```

## Implementation Example: GRN Page

The Goods Receipt page demonstrates the full implementation:

**File**: `frontend/src/pages/Inventory/GoodsReceipts/GoodsReceiptManagementNew.jsx`

**Features Implemented**:
1. ✅ Unified layout with breadcrumbs and actions
2. ✅ KPI stats cards (Total, Pending QC, Approved, On Hold)
3. ✅ Smart filters with quick filters
4. ✅ View toggle (Table / Kanban)
5. ✅ Workflow board for status visualization
6. ✅ Table view with inline actions
7. ✅ Drawer for create/edit forms
8. ✅ Responsive design

## Page Template

Use this template for creating new inventory pages:

```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { Button, Table, Drawer, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  InventoryLayout,
  SmartFilters,
  InventoryStats,
  ViewToggle,
} from '../../../components/Inventory';
import { useCompany } from '../../../contexts/CompanyContext';
import * as service from '../../../services/yourService';

const YourPage = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [filters, setFilters] = useState({});
  const [viewMode, setViewMode] = useState('table');

  const fetchData = useCallback(async () => {
    if (!currentCompany?.id) return;
    try {
      setLoading(true);
      const response = await service.getData({ company: currentCompany.id });
      setData(response.data?.results || response.data || []);
    } catch (error) {
      message.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [currentCompany]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const stats = [
    {
      key: 'total',
      title: 'Total Items',
      value: data.length,
      icon: <YourIcon />,
    },
  ];

  const filterConfig = [
    {
      type: 'select',
      field: 'status',
      label: 'Status',
      options: [],
    },
  ];

  return (
    <InventoryLayout
      title="Your Page Title"
      icon={<YourIcon />}
      subtitle="Description"
      breadcrumb={[
        { label: 'Inventory', path: '/inventory' },
        { label: 'Category' },
        { label: 'Page Title' },
      ]}
      actions={[
        <Button key="refresh" icon={<ReloadOutlined />} onClick={fetchData}>
          Refresh
        </Button>,
        <Button key="create" type="primary" icon={<PlusOutlined />}>
          Create New
        </Button>,
      ]}
    >
      <InventoryStats stats={stats} loading={loading} />

      <SmartFilters
        filters={filterConfig}
        onFilterChange={setFilters}
      />

      <ViewToggle
        value={viewMode}
        onChange={setViewMode}
        views={['table', 'cards']}
      />

      {/* Content based on view mode */}
      {viewMode === 'table' && (
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
        />
      )}
    </InventoryLayout>
  );
};

export default YourPage;
```

## Best Practices

### 1. Consistent Patterns
- Always use `InventoryLayout` for page wrapper
- Include breadcrumbs for navigation context
- Provide refresh and create actions where applicable

### 2. Smart Filtering
- Use quick filters for common scenarios
- Enable saved filters for power users
- Include search for text-based filtering

### 3. Stats Display
- Show 3-4 key metrics per page
- Make stats clickable to apply filters
- Use trends to show change over time
- Use progress bars for goals/targets

### 4. View Modes
- Offer Table view as default
- Add Kanban for workflow-heavy pages
- Consider Cards view for visual content

### 5. Performance
- Use `useCallback` for fetch functions
- Memoize computed values with `useMemo`
- Implement proper loading states
- Handle errors gracefully

### 6. Accessibility
- Provide keyboard navigation
- Use ARIA labels
- Ensure color contrast
- Support screen readers

## Migration Guide

To migrate existing pages to the new UI:

1. **Replace page wrapper** with `InventoryLayout`
2. **Add breadcrumbs** for navigation context
3. **Extract statistics** into `InventoryStats` component
4. **Convert filters** to `SmartFilters` format
5. **Add view toggle** if multiple views make sense
6. **Use drawers** instead of modals for forms
7. **Test keyboard shortcuts** (Ctrl+K)
8. **Verify mobile responsiveness**

## Keyboard Shortcuts

Global shortcuts:
- **Ctrl+K** / **Cmd+K**: Open Command Palette
- **Ctrl+/** / **Cmd+/**: Focus search (within pages)

Command Palette shortcuts:
- **↑ ↓**: Navigate commands
- **Enter**: Execute selected command
- **Escape**: Close palette

## Future Enhancements

Planned improvements:
- [ ] Bulk operations component
- [ ] Export/Import wizard
- [ ] Timeline view mode
- [ ] Custom dashboard builder
- [ ] Mobile app version
- [ ] Offline mode support
- [ ] Advanced reporting component
- [ ] Notification center integration

## Support

For questions or issues:
- Check component documentation
- Review the GRN page implementation
- Refer to Ant Design documentation
- Contact the development team

---

**Last Updated**: November 2025
**Version**: 1.0
**Author**: Development Team
