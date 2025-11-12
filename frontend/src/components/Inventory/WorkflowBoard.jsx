import React from 'react';
import { Card, Tag, Space, Typography, Badge, Tooltip, Empty, Avatar } from 'antd';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import {
  ClockCircleOutlined,
  UserOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

/**
 * WorkflowBoard - Kanban-style workflow board with drag and drop
 * Perfect for GRN workflow, Material Issue status tracking, etc.
 */
const WorkflowBoard = ({
  columns = [],
  items = {},
  onDragEnd,
  renderItem,
  loading = false,
  emptyText = 'No items',
}) => {
  const handleDragEnd = (result) => {
    if (!result.destination) {
      return;
    }

    if (onDragEnd) {
      onDragEnd(result);
    }
  };

  const getColumnStyle = (column) => ({
    background: column.color || '#f5f5f5',
    padding: 16,
    borderRadius: 8,
    minHeight: 500,
  });

  const getItemStyle = (isDragging, draggableStyle) => ({
    userSelect: 'none',
    marginBottom: 8,
    ...draggableStyle,
  });

  const defaultRenderItem = (item, column) => {
    return (
      <Card
        size="small"
        hoverable
        style={{
          borderLeft: `3px solid ${column.statusColor || '#1890ff'}`,
        }}
      >
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          {/* Item Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
            <Text strong style={{ fontSize: 13 }}>
              {item.code || item.id}
            </Text>
            {item.priority && (
              <Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'default'} style={{ margin: 0 }}>
                {item.priority}
              </Tag>
            )}
          </div>

          {/* Item Description */}
          <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
            {item.description || item.name || item.title}
          </Text>

          {/* Item Meta */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
            {item.assignee && (
              <Tooltip title={item.assignee}>
                <Avatar size="small" icon={<UserOutlined />} style={{ fontSize: 12 }}>
                  {item.assignee.substring(0, 2).toUpperCase()}
                </Avatar>
              </Tooltip>
            )}
            {item.dueDate && (
              <Space size={4}>
                <ClockCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {item.dueDate}
                </Text>
              </Space>
            )}
            {item.count && (
              <Badge
                count={item.count}
                style={{ backgroundColor: '#52c41a' }}
                showZero
              />
            )}
          </div>

          {/* Additional Info */}
          {item.tags && (
            <div style={{ marginTop: 4 }}>
              {item.tags.map((tag, idx) => (
                <Tag key={idx} style={{ fontSize: 11, padding: '0 4px', marginRight: 4 }}>
                  {tag}
                </Tag>
              ))}
            </div>
          )}
        </Space>
      </Card>
    );
  };

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16 }}>
        {columns.map((column) => {
          const columnItems = (column.itemIds || [])
            .map((itemId) => items[itemId])
            .filter(Boolean);

          return (
            <div
              key={column.id}
              style={{
                flex: '1 1 300px',
                minWidth: 300,
                maxWidth: 400,
              }}
            >
              {/* Column Header */}
              <Card
                size="small"
                style={{
                  marginBottom: 8,
                  background: column.headerColor || '#fafafa',
                  borderRadius: 8,
                }}
                bodyStyle={{ padding: '12px 16px' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    <Title level={5} style={{ margin: 0 }}>
                      {column.title}
                    </Title>
                    <Badge
                      count={columnItems.length}
                      style={{
                        backgroundColor: column.badgeColor || '#1890ff',
                      }}
                      showZero
                    />
                  </Space>
                  {column.info && (
                    <Tooltip title={column.info}>
                      <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                    </Tooltip>
                  )}
                </div>
                {column.description && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {column.description}
                  </Text>
                )}
              </Card>

              {/* Droppable Column */}
              <Droppable droppableId={column.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    style={{
                      ...getColumnStyle(column),
                      background: snapshot.isDraggingOver ? '#e6f7ff' : column.color || '#f5f5f5',
                    }}
                  >
                    {columnItems.length === 0 ? (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={emptyText}
                        style={{ padding: '40px 0' }}
                      />
                    ) : (
                      columnItems.map((item, index) => (
                        <Draggable
                          key={item.id}
                          draggableId={item.id.toString()}
                          index={index}
                        >
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              style={getItemStyle(
                                snapshot.isDragging,
                                provided.draggableProps.style
                              )}
                            >
                              {renderItem
                                ? renderItem(item, column)
                                : defaultRenderItem(item, column)}
                            </div>
                          )}
                        </Draggable>
                      ))
                    )}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </div>
          );
        })}
      </div>
    </DragDropContext>
  );
};

export default WorkflowBoard;
