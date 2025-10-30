import React, { useEffect, useMemo, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Space,
  Segmented,
  Typography,
  List,
  Button,
  Tag,
} from 'antd';
import {
  ThunderboltOutlined,
  FileProtectOutlined,
  ScheduleOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import api from '../../../services/api';
import { useCompany } from '../../../contexts/CompanyContext';

const { Title, Text } = Typography;

const INITIAL_PIPELINE = {
  columns: {
    'stage-prospecting': {
      id: 'stage-prospecting',
      title: 'Prospecting',
      kpi: 'Average age: 4 days',
      itemIds: ['deal-201', 'deal-202'],
    },
    'stage-qualification': {
      id: 'stage-qualification',
      title: 'Qualification',
      kpi: 'Discovery complete: 68%',
      itemIds: ['deal-203', 'deal-204'],
    },
    'stage-proposal': {
      id: 'stage-proposal',
      title: 'Proposal',
      kpi: 'Value in stage: ৳4.8M',
      itemIds: ['deal-205'],
    },
    'stage-negotiation': {
      id: 'stage-negotiation',
      title: 'Negotiation',
      kpi: 'Commitment probability: 72%',
      itemIds: ['deal-206'],
    },
    'stage-closed': {
      id: 'stage-closed',
      title: 'Closed Won',
      kpi: 'Quarter wins: ৳6.2M',
      itemIds: ['deal-207'],
    },
  },
  items: {
    'deal-201': {
      id: 'deal-201',
      account: 'Aurora Retail',
      value: 480000,
      owner: 'Sajid Khan',
      probability: '20%',
      nextAction: 'Discovery call Friday',
    },
    'deal-202': {
      id: 'deal-202',
      account: 'Velocity Sports',
      value: 390000,
      owner: 'Lamia Hasan',
      probability: '15%',
      nextAction: 'Send capability deck',
    },
    'deal-203': {
      id: 'deal-203',
      account: 'Silverline Foods',
      value: 820000,
      owner: 'Sara Karim',
      probability: '35%',
      nextAction: 'Technical validation',
    },
    'deal-204': {
      id: 'deal-204',
      account: 'Lotus Garments',
      value: 710000,
      owner: 'Rahim Uddin',
      probability: '32%',
      nextAction: 'Budget alignment',
    },
    'deal-205': {
      id: 'deal-205',
      account: 'Orion Home',
      value: 1250000,
      owner: 'Sajid Khan',
      probability: '55%',
      nextAction: 'Proposal review with CFO',
    },
    'deal-206': {
      id: 'deal-206',
      account: 'Dakota Fashion',
      value: 1620000,
      owner: 'Lamia Hasan',
      probability: '72%',
      nextAction: 'Finalize commercials',
    },
    'deal-207': {
      id: 'deal-207',
      account: 'Acme Textiles',
      value: 2450000,
      owner: 'Rahim Uddin',
      probability: 'Won',
      nextAction: 'Handover to delivery',
    },
  },
};

const SalesPipeline = () => {
  const { currentCompany } = useCompany();
  const [board, setBoard] = useState(INITIAL_PIPELINE);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('PIPELINE');

  useEffect(() => {
    loadPipeline();
  }, [currentCompany]);

  const loadPipeline = async () => {
    try {
      setLoading(true);
      if (!currentCompany || Number.isNaN(Number(currentCompany.id))) {
        setBoard(JSON.parse(JSON.stringify(INITIAL_PIPELINE)));
        return;
      }
      const response = await api.get('/api/v1/sales/pipeline/');
      const payload = response.data || {};
      if (payload.columns && payload.items) {
        setBoard(payload);
      } else {
        setBoard(JSON.parse(JSON.stringify(INITIAL_PIPELINE)));
      }
    } catch (error) {
      console.warn('Sales pipeline fallback data used:', error?.message);
      setBoard(JSON.parse(JSON.stringify(INITIAL_PIPELINE)));
    } finally {
      setLoading(false);
    }
  };

  const handleDragEnd = (result) => {
    const { destination, source, draggableId } = result;
    if (!destination) {
      return;
    }
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    setBoard((prev) => {
      const startColumn = prev.columns[source.droppableId];
      const finishColumn = prev.columns[destination.droppableId];
      if (!startColumn || !finishColumn) {
        return prev;
      }
      if (startColumn === finishColumn) {
        const newItemIds = Array.from(startColumn.itemIds);
        newItemIds.splice(source.index, 1);
        newItemIds.splice(destination.index, 0, draggableId);
        return {
          ...prev,
          columns: {
            ...prev.columns,
            [startColumn.id]: { ...startColumn, itemIds: newItemIds },
          },
        };
      }
      const startItemIds = Array.from(startColumn.itemIds);
      startItemIds.splice(source.index, 1);
      const newStartColumn = { ...startColumn, itemIds: startItemIds };

      const finishItemIds = Array.from(finishColumn.itemIds);
      finishItemIds.splice(destination.index, 0, draggableId);
      const newFinishColumn = { ...finishColumn, itemIds: finishItemIds };

      return {
        ...prev,
        columns: {
          ...prev.columns,
          [newStartColumn.id]: newStartColumn,
          [newFinishColumn.id]: newFinishColumn,
        },
      };
    });
  };

  const boardTotals = useMemo(() => {
    const totals = {};
    Object.values(board.columns).forEach((column) => {
      totals[column.id] = column.itemIds.reduce((sum, itemId) => {
        const deal = board.items[itemId];
        return sum + (deal?.value || 0);
      }, 0);
    });
    return totals;
  }, [board]);

  return (
    <div>
      <Title level={2}>Pipeline Management</Title>
      <Text type="secondary">
        Drag deals across stages, trigger playbooks, and coordinate teamwork across the revenue
        lifecycle.
      </Text>

      <Space style={{ marginTop: 16, marginBottom: 16 }}>
        <Segmented
          options={[
            { label: 'Kanban Board', value: 'PIPELINE' },
            { label: 'Capacity View', value: 'CAPACITY' },
          ]}
          value={viewMode}
          onChange={setViewMode}
        />
        <Button icon={<ThunderboltOutlined />}>AI Deal Coach</Button>
        <Button icon={<FileProtectOutlined />}>Forecast Snapshot</Button>
      </Space>

      {viewMode === 'PIPELINE' ? (
        <DragDropContext onDragEnd={handleDragEnd}>
          <Row gutter={[16, 16]}>
            {Object.values(board.columns).map((column) => (
              <Col xs={24} md={12} xl={4} key={column.id}>
                <Card
                  loading={loading}
                  title={
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space align="baseline" style={{ justifyContent: 'space-between' }}>
                        <Text strong>{column.title}</Text>
                        <Tag color="blue">৳ {boardTotals[column.id]?.toLocaleString()}</Tag>
                      </Space>
                      <Text type="secondary">{column.kpi}</Text>
                    </Space>
                  }
                  bodyStyle={{ padding: 12, minHeight: 260 }}
                >
                  <Droppable droppableId={column.id}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        style={{
                          minHeight: 220,
                          background: snapshot.isDraggingOver ? '#f0f5ff' : 'transparent',
                          borderRadius: 8,
                          padding: 4,
                        }}
                      >
                        {column.itemIds.map((itemId, index) => {
                          const deal = board.items[itemId];
                          if (!deal) {
                            return null;
                          }
                          return (
                            <Draggable draggableId={itemId} index={index} key={itemId}>
                              {(dragProvided, dragSnapshot) => (
                                <Card
                                  size="small"
                                  ref={dragProvided.innerRef}
                                  {...dragProvided.draggableProps}
                                  {...dragProvided.dragHandleProps}
                                  style={{
                                    marginBottom: 8,
                                    boxShadow: dragSnapshot.isDragging
                                      ? '0 8px 16px rgba(82, 196, 26, 0.2)'
                                      : '0 1px 3px rgba(0,0,0,0.1)',
                                    border: '1px solid #f0f0f0',
                                  }}
                                >
                                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                                    <Space
                                      align="baseline"
                                      style={{ justifyContent: 'space-between', width: '100%' }}
                                    >
                                      <Text strong>{deal.account}</Text>
                                      <Tag color="blue">
                                        ৳ {(deal.value || 0).toLocaleString()}
                                      </Tag>
                                    </Space>
                                    <Space
                                      align="baseline"
                                      style={{ justifyContent: 'space-between', width: '100%' }}
                                    >
                                      <Text type="secondary">{deal.owner}</Text>
                                      <Tag color="purple">{deal.probability}</Tag>
                                    </Space>
                                    <Text type="secondary">{deal.nextAction}</Text>
                                  </Space>
                                </Card>
                              )}
                            </Draggable>
                          );
                        })}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </Card>
              </Col>
            ))}
          </Row>
        </DragDropContext>
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="Team Capacity">
              <List
                dataSource={[
                  { id: 'cap-1', owner: 'Rahim Uddin', deals: 14, load: 'High' },
                  { id: 'cap-2', owner: 'Sara Karim', deals: 9, load: 'Optimal' },
                  { id: 'cap-3', owner: 'Lamia Hasan', deals: 11, load: 'Optimal' },
                  { id: 'cap-4', owner: 'Sajid Khan', deals: 7, load: 'Light' },
                ]}
                renderItem={(item) => (
                  <List.Item key={item.id}>
                    <Space>
                      <TeamOutlined />
                      <Space direction="vertical" size={0}>
                        <Text strong>{item.owner}</Text>
                        <Text type="secondary">
                          {item.deals} active deals · Load: {item.load}
                        </Text>
                      </Space>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Upcoming Milestones">
              <List
                dataSource={[
                  { id: 'mile-1', title: 'Quarter Forecast Gate', detail: 'Friday · Sales Ops' },
                  { id: 'mile-2', title: 'Executive Deal Review', detail: 'Monday · 10 AM' },
                  { id: 'mile-3', title: 'Renewal Blitz', detail: 'Next Week · Customer Success' },
                ]}
                renderItem={(item) => (
                  <List.Item key={item.id}>
                    <Space>
                      <ScheduleOutlined style={{ color: '#1890ff' }} />
                      <Space direction="vertical" size={0}>
                        <Text strong>{item.title}</Text>
                        <Text type="secondary">{item.detail}</Text>
                      </Space>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default SalesPipeline;
