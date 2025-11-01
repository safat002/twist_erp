import React, { useEffect, useMemo, useState } from 'react';
import { Card, Col, List, Progress, Row, Space, Statistic, Tag, Typography, message } from 'antd';
import {
  ApartmentOutlined,
  ClusterOutlined,
  FundProjectionScreenOutlined,
  ReconciliationOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { fetchBOMs, fetchCapacitySummary, fetchMRPSummary, fetchWorkOrders } from '../../services/production';

const { Title, Text } = Typography;

const ProductionWorkspace = () => {
  const [loading, setLoading] = useState(false);
  const [workOrders, setWorkOrders] = useState([]);
  const [summary, setSummary] = useState({});
  const [boms, setBoms] = useState([]);
  const [mrp, setMrp] = useState([]);
  const [demand, setDemand] = useState({});
  const [capacity, setCapacity] = useState({ buckets: [], default_capacity: 16 });

  const loadWorkspace = async () => {
    try {
      setLoading(true);
      const horizonParams = {
        from_date: dayjs().format('YYYY-MM-DD'),
        to_date: dayjs().add(14, 'day').format('YYYY-MM-DD'),
        include_sales: true,
      };
      const [{ data: woData }, { data: bomData }, { data: mrpData }, { data: capacityData }] =
        await Promise.all([
          fetchWorkOrders(),
          fetchBOMs({ status: 'ACTIVE', limit: 5 }),
          fetchMRPSummary(horizonParams),
          fetchCapacitySummary(horizonParams),
        ]);

      setWorkOrders(Array.isArray(woData?.results) ? woData.results : []);
      setSummary(woData?.summary || {});
      setBoms(Array.isArray(bomData?.results) ? bomData.results : []);
      setMrp(Array.isArray(mrpData?.recommendations) ? mrpData.recommendations : []);
      setDemand(mrpData?.demand || {});
      setCapacity(capacityData || { buckets: [], default_capacity: 16 });
    } catch (error) {
      console.warn('Failed to load production workspace', error?.message);
      message.error('Unable to load production overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, []);

  const keyStats = useMemo(() => {
    const planned = Number(summary?.PLANNED || 0);
    const inProgress = Number(summary?.IN_PROGRESS || 0);
    const completed = Number(summary?.COMPLETED || 0);
    const total = planned + inProgress + completed + Number(summary?.RELEASED || 0);
    return { planned, inProgress, completed, total };
  }, [summary]);

  const upcomingWorkOrders = useMemo(
    () =>
      workOrders
        .filter((wo) => wo.status !== 'COMPLETED')
        .slice(0, 5)
        .map((wo) => ({
          id: wo.id,
          number: wo.number,
          product: wo.product,
          status: wo.status,
          quantity: wo.quantity_planned,
          start: wo.scheduled_start ? dayjs(wo.scheduled_start).format('YYYY-MM-DD') : 'TBD',
          end: wo.scheduled_end ? dayjs(wo.scheduled_end).format('YYYY-MM-DD') : 'TBD',
        })),
    [workOrders],
  );

  const capacityBuckets = useMemo(() => capacity?.buckets || [], [capacity]);
  const salesDemand = useMemo(() => demand?.sales_orders || [], [demand]);

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space>
          <FundProjectionScreenOutlined style={{ fontSize: 28 }} />
          <div>
            <Title level={3} style={{ margin: 0 }}>
              Production Control Tower
            </Title>
            <Text type="secondary">
              Real-time view of manufacturing execution - {dayjs().format('MMMM D, YYYY')}
            </Text>
          </div>
        </Space>
      </Space>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="Open Work Orders" value={keyStats.total} prefix={<ApartmentOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="Planned" value={keyStats.planned} />
          </Card>
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="In Progress" value={keyStats.inProgress} />
          </Card>
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Card bordered={false} loading={loading}>
            <Statistic title="Completed" value={keyStats.completed} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card
            title="Upcoming Work Orders"
            bordered={false}
            loading={loading}
            extra={<Text type="secondary">Top 5</Text>}
          >
            <List
              dataSource={upcomingWorkOrders}
              locale={{ emptyText: 'No open work orders.' }}
              renderItem={(item) => (
                <List.Item>
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                      <Text strong>{item.number}</Text>
                      <Tag color={item.status === 'IN_PROGRESS' ? 'blue' : 'default'}>{item.status}</Tag>
                    </Space>
                                          <Text type="secondary">
                                            {`Planned Qty: ${item.quantity} - ${item.start} -> ${item.end}`}
                                          </Text>                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Active Bills of Material" bordered={false} loading={loading}>
            <List
              dataSource={boms.slice(0, 5)}
              locale={{ emptyText: 'No active BOMs yet.' }}
              renderItem={(item) => (
                <List.Item>
                  <Space direction="vertical" size={0}>
                    <Text strong>{item.code}</Text>
                    <Text type="secondary">{item.name || 'Unnamed BOM'} - v{item.version}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <ClusterOutlined />
                <span>MRP Shortage Recommendations</span>
              </Space>
            }
            bordered={false}
            loading={loading}
          >
            <List
              dataSource={mrp}
              locale={{ emptyText: 'No component shortages detected.' }}
              renderItem={(item) => (
                <List.Item>
                  <Space direction="vertical" size={0}>
                    <Tag color="volcano">{item.shortage}</Tag>
                    <Text>Product ID #{item.product}</Text>
                    <Text type="secondary">
                      Required {item.required_quantity} - On-hand {item.on_hand}
                    </Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <ReconciliationOutlined />
                <span>Order-Driven Demand</span>
              </Space>
            }
            bordered={false}
            loading={loading}
          >
            <List
              dataSource={salesDemand.slice(0, 6)}
              locale={{ emptyText: 'No pending sales orders impacting capacity.' }}
              renderItem={(item) => (
                <List.Item>
                  <Space direction="vertical" size={0}>
                    <Text strong>{item.order}</Text>
                    <Text type="secondary">
                      Product #{item.product} - Due {item.due || 'TBD'} - Outstanding {item.outstanding}
                    </Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <ApartmentOutlined />
            <span>Capacity Load (Next 2 Weeks)</span>
          </Space>
        }
        bordered={false}
        loading={loading}
      >
        <List
          dataSource={capacityBuckets}
          locale={{ emptyText: 'No work orders scheduled in this horizon.' }}
          renderItem={(item) => {
            const planned = Number(item.planned_hours || 0);
            const available =
              Number(item.available_hours || capacity.default_capacity || 0) || 1;
            const percentage = Math.min(100, Math.round((planned / available) * 100));
            const overloaded = planned > available;
            return (
              <List.Item>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Text strong>{dayjs(item.date).format('MMM D, YYYY')}</Text>
                    <Text type="secondary">
                      Planned {planned.toFixed(1)}h / Capacity {available.toFixed(1)}h
                    </Text>
                  </Space>
                  <Progress percent={percentage} status={overloaded ? 'exception' : 'active'} />
                </Space>
              </List.Item>
            );
          }}
        />
      </Card>
    </Space>
  );
};

export default ProductionWorkspace;
