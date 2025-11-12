import React from 'react';
import { Segmented, Space } from 'antd';
import {
  TableOutlined,
  AppstoreOutlined,
  ProjectOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
} from '@ant-design/icons';

/**
 * ViewToggle - Component for switching between different view modes
 * Supports Table, Cards, Kanban, List, and Chart views
 */
const ViewToggle = ({
  value = 'table',
  onChange,
  views = ['table', 'cards', 'kanban'],
  size = 'middle',
  style = {},
}) => {
  const viewOptions = {
    table: {
      label: 'Table',
      value: 'table',
      icon: <TableOutlined />,
    },
    cards: {
      label: 'Cards',
      value: 'cards',
      icon: <AppstoreOutlined />,
    },
    kanban: {
      label: 'Kanban',
      value: 'kanban',
      icon: <ProjectOutlined />,
    },
    list: {
      label: 'List',
      value: 'list',
      icon: <UnorderedListOutlined />,
    },
    chart: {
      label: 'Chart',
      value: 'chart',
      icon: <BarChartOutlined />,
    },
  };

  const options = views.map((view) => ({
    label: (
      <Space>
        {viewOptions[view].icon}
        {viewOptions[view].label}
      </Space>
    ),
    value: viewOptions[view].value,
  }));

  return (
    <Segmented
      options={options}
      value={value}
      onChange={onChange}
      size={size}
      style={style}
    />
  );
};

export default ViewToggle;
