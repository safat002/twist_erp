import React, { useEffect, useMemo, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Tag, DatePicker } from 'antd';
import { App as AntApp } from 'antd';
import { Column, Pie } from '@ant-design/charts';
import api from '../../services/api';

const NgoDashboard = () => {
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();
  const [data, setData] = useState({ totals: {}, programs: [] });

  const [range, setRange] = useState([]);
  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (Array.isArray(range) && range.length === 2) {
        params.from = range[0].format('YYYY-MM-DD');
        params.to = range[1].format('YYYY-MM-DD');
      }
      const { data } = await api.get('/api/v1/ngo/programs/overview/', { params });
      setData(data || { totals: {}, programs: [] });
    } catch (e) {
      message.error('Failed to load overview');
      setData({ totals: {}, programs: [] });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [range]);

  const programsCols = [
    { title: 'Code', dataIndex: 'code' },
    { title: 'Title', dataIndex: 'title' },
    { title: 'Status', dataIndex: 'status', render: (v) => <Tag color={v==='active'?'green':v==='closed'?'default':'gold'}>{String(v || '').toUpperCase()}</Tag> },
    { title: 'Active Reqs', dataIndex: 'requirements_count' },
    { title: 'Overdue', dataIndex: 'overdue_count' },
    { title: 'Next Due', dataIndex: 'next_due' },
  ];

  const t = data.totals || {};

  const statusData = useMemo(() => {
    const counts = { draft: 0, active: 0, closed: 0 };
    (data.programs || []).forEach(p => { counts[p.status] = (counts[p.status] || 0) + 1; });
    return [
      { type: 'Draft', value: counts.draft || 0 },
      { type: 'Active', value: counts.active || 0 },
      { type: 'Closed', value: counts.closed || 0 },
    ];
  }, [data]);

  const overdueData = useMemo(() => (data.programs || []).map(p => ({ program: p.code, overdue: p.overdue_count || 0 })), [data]);

  return (
    <div>
      <Row gutter={[16,16]}>
        <Col xs={24} md={8}><Card loading={loading}><Statistic title="Programs" value={t.total_programs || 0} /></Card></Col>
        <Col xs={24} md={8}><Card loading={loading}><Statistic title="Active Programs" value={t.active_programs || 0} /></Card></Col>
        <Col xs={24} md={8}><Card loading={loading}><Statistic title="Closed Programs" value={t.closed_programs || 0} /></Card></Col>
        <Col xs={24} md={8}><Card loading={loading}><Statistic title="Requirements" value={t.total_requirements || 0} /></Card></Col>
        <Col xs={24} md={8}><Card loading={loading}><Statistic title="Due in 30d" value={t.requirements_due_30 || 0} /></Card></Col>
        <Col xs={24} md={8}><Card loading={loading}><Statistic title="Overdue" value={t.requirements_overdue || 0} valueStyle={{ color: '#cf1322' }} /></Card></Col>
      </Row>

      <Card title="Filters" style={{ marginTop: 16 }}>
        <DatePicker.RangePicker onChange={setRange} />
      </Card>

      <Row gutter={[16,16]} style={{ marginTop: 8 }}>
        <Col xs={24} md={12}>
          <Card title="Program Status Breakdown" loading={loading}>
            <Pie data={statusData} angleField="value" colorField="type" radius={0.8} legend={{ position: 'bottom' }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Overdue by Program" loading={loading}>
            <Column data={overdueData} xField="program" yField="overdue" columnWidthRatio={0.5} />
          </Card>
        </Col>
      </Row>

      <Card title="Program Compliance" style={{ marginTop: 16 }} loading={loading}>
        <Table columns={programsCols} dataSource={data.programs || []} rowKey={(r) => r.id} pagination={{ pageSize: 10 }} />
      </Card>
    </div>
  );
};

export default NgoDashboard;
