import React, { useState, useEffect, useCallback } from 'react';
import { Modal, Input, List, Typography, Tag, Space, Empty } from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  InboxOutlined,
  SendOutlined,
  SwapOutlined,
  FileOutlined,
  SettingOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

/**
 * CommandPalette - Quick command/search interface (Ctrl+K)
 * Allows users to quickly navigate and perform actions
 */
const CommandPalette = ({ visible, onClose, commands = [] }) => {
  const [searchText, setSearchText] = useState('');
  const [filteredCommands, setFilteredCommands] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();

  // Default commands
  const defaultCommands = [
    {
      id: 'new-grn',
      title: 'New Goods Receipt (GRN)',
      description: 'Create a new goods receipt note',
      icon: <InboxOutlined />,
      category: 'Create',
      keywords: ['create', 'new', 'grn', 'goods', 'receipt', 'receive'],
      action: () => navigate('/inventory/goods-receipts'),
    },
    {
      id: 'new-material-issue',
      title: 'New Material Issue',
      description: 'Issue materials to department or production',
      icon: <SendOutlined />,
      category: 'Create',
      keywords: ['create', 'new', 'material', 'issue', 'send'],
      action: () => navigate('/inventory/material-issues'),
    },
    {
      id: 'new-requisition',
      title: 'New Requisition',
      description: 'Create internal requisition',
      icon: <FileOutlined />,
      category: 'Create',
      keywords: ['create', 'new', 'requisition', 'request'],
      action: () => navigate('/inventory/requisitions'),
    },
    {
      id: 'new-rtv',
      title: 'Return to Vendor',
      description: 'Create return to vendor',
      icon: <SwapOutlined />,
      category: 'Create',
      keywords: ['create', 'new', 'return', 'vendor', 'rtv'],
      action: () => navigate('/inventory/return-to-vendor'),
    },
    {
      id: 'goto-dashboard',
      title: 'Inventory Dashboard',
      description: 'Go to inventory control tower',
      icon: <DashboardOutlined />,
      category: 'Navigate',
      keywords: ['dashboard', 'inventory', 'control', 'tower', 'overview'],
      action: () => navigate('/inventory'),
    },
    {
      id: 'goto-products',
      title: 'Products & Items',
      description: 'Manage products and items',
      icon: <FileOutlined />,
      category: 'Navigate',
      keywords: ['products', 'items', 'master', 'data'],
      action: () => navigate('/inventory/products'),
    },
    {
      id: 'goto-warehouses',
      title: 'Warehouses',
      description: 'Manage warehouses and locations',
      icon: <SettingOutlined />,
      category: 'Navigate',
      keywords: ['warehouses', 'locations', 'bins'],
      action: () => navigate('/inventory/warehouses'),
    },
    {
      id: 'goto-movements',
      title: 'Stock Movements',
      description: 'View stock movement history',
      icon: <SwapOutlined />,
      category: 'Navigate',
      keywords: ['movements', 'stock', 'transfers', 'history'],
      action: () => navigate('/inventory/movements'),
    },
    {
      id: 'goto-valuation',
      title: 'Inventory Valuation',
      description: 'View inventory valuation reports',
      icon: <FileOutlined />,
      category: 'Navigate',
      keywords: ['valuation', 'cost', 'value', 'report'],
      action: () => navigate('/inventory/valuation/report'),
    },
    {
      id: 'goto-qc',
      title: 'Quality Control',
      description: 'Manage quality inspections',
      icon: <SettingOutlined />,
      category: 'Navigate',
      keywords: ['quality', 'qc', 'inspection', 'control'],
      action: () => navigate('/inventory/quality-control'),
    },
  ];

  const allCommands = [...defaultCommands, ...commands];

  // Filter commands based on search
  useEffect(() => {
    if (!searchText) {
      setFilteredCommands(allCommands);
      setSelectedIndex(0);
      return;
    }

    const searchLower = searchText.toLowerCase();
    const filtered = allCommands.filter((cmd) => {
      const titleMatch = cmd.title.toLowerCase().includes(searchLower);
      const descMatch = cmd.description?.toLowerCase().includes(searchLower);
      const keywordMatch = cmd.keywords?.some((kw) => kw.includes(searchLower));
      return titleMatch || descMatch || keywordMatch;
    });

    setFilteredCommands(filtered);
    setSelectedIndex(0);
  }, [searchText]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e) => {
      if (!visible) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < filteredCommands.length - 1 ? prev + 1 : prev
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            executeCommand(filteredCommands[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          handleClose();
          break;
        default:
          break;
      }
    },
    [visible, selectedIndex, filteredCommands]
  );

  useEffect(() => {
    if (visible) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [visible, handleKeyDown]);

  const executeCommand = (command) => {
    if (command.action) {
      command.action();
    }
    handleClose();
  };

  const handleClose = () => {
    setSearchText('');
    setSelectedIndex(0);
    onClose();
  };

  const getCategoryColor = (category) => {
    const colors = {
      Create: 'blue',
      Navigate: 'green',
      Action: 'orange',
      Settings: 'purple',
    };
    return colors[category] || 'default';
  };

  const getCategoryIcon = (category) => {
    const icons = {
      Create: <PlusOutlined />,
      Navigate: <DashboardOutlined />,
      Action: <SendOutlined />,
      Settings: <SettingOutlined />,
    };
    return icons[category] || null;
  };

  return (
    <Modal
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={600}
      style={{ top: 100 }}
      bodyStyle={{ padding: 0 }}
      closable={false}
    >
      {/* Search Input */}
      <div style={{ padding: '16px 16px 0 16px' }}>
        <Input
          autoFocus
          size="large"
          placeholder="Type a command or search..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          bordered={false}
          style={{ fontSize: 16 }}
        />
      </div>

      {/* Command List */}
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        {filteredCommands.length === 0 ? (
          <Empty
            description="No commands found"
            style={{ padding: '40px 0' }}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            dataSource={filteredCommands}
            renderItem={(command, index) => (
              <List.Item
                key={command.id}
                onClick={() => executeCommand(command)}
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  background: index === selectedIndex ? '#e6f7ff' : 'transparent',
                  borderLeft: index === selectedIndex ? '3px solid #1890ff' : '3px solid transparent',
                }}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <List.Item.Meta
                  avatar={
                    <div style={{ fontSize: 24, color: '#1890ff' }}>
                      {command.icon}
                    </div>
                  }
                  title={
                    <Space>
                      <Text strong>{command.title}</Text>
                      {command.category && (
                        <Tag
                          color={getCategoryColor(command.category)}
                          icon={getCategoryIcon(command.category)}
                          style={{ fontSize: 11 }}
                        >
                          {command.category}
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {command.description}
                    </Text>
                  }
                />
                {command.shortcut && (
                  <Tag style={{ fontSize: 11 }}>{command.shortcut}</Tag>
                )}
              </List.Item>
            )}
          />
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '8px 16px',
          borderTop: '1px solid #f0f0f0',
          background: '#fafafa',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <Space size={16}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            <Tag style={{ fontSize: 11 }}>↑↓</Tag> Navigate
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            <Tag style={{ fontSize: 11 }}>Enter</Tag> Select
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            <Tag style={{ fontSize: 11 }}>Esc</Tag> Close
          </Text>
        </Space>
      </div>
    </Modal>
  );
};

export default CommandPalette;
