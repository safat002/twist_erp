import React, { useEffect, useMemo, useState } from 'react';
import { Card, Col, Row, Statistic, Table, DatePicker } from 'antd';
import { App as AntApp } from 'antd';
import { Column } from '@ant-design/charts';
import api from '../../services/api';

const MicrofinanceDashboard = () => {
  const [loading, setLoading] = useState(false);
  const [par, setPar] = useState({});
  const [overdue, setOverdue] = useState([]);
  const [asOf, setAsOf] = useState(null);
  const [days, setDays] = useState(30);
  const { message } = AntApp.useApp();

  const load = async () => {
    setLoading(true);
    try {
      const parParams = {};
      if (asOf) parParams.as_of = asOf.format('YYYY-MM-DD');
      const [p, o] = await Promise.all([
        api.get('/api/v1/microfinance/loans/par/', { params: parParams }),
        api.get('/api/v1/microfinance/loans/overdue/', { params: { days } }),
      ]);
      setPar(p.data || {});
      setOverdue(Array.isArray(o.data) ? o.data : o.data?.results || []);
    } catch (e) {
      message.error('Failed to load microfinance metrics');
      setPar({});
      setOverdue([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [asOf, days]);

  const cols = [
    { title: 'Loan', dataIndex: 'loan__number' },
    { title: 'Borrower', dataIndex: 'loan__borrower__name' },
    { title: 'Installment', dataIndex: 'installment_number' },
    { title: 'Due Date', dataIndex: 'due_date' },
    { title: 'Due Amount', dataIndex: 'due_amount' },
  ];

  const parData = useMemo(() => ([
    { bucket: 'PAR30', value: Number(par.par30 || 0) },
    { bucket: 'PAR60', value: Number(par.par60 || 0) },
    { bucket: 'PAR90', value: Number(par.par90 || 0) },
  ]), [par]);

  return (
    <div>
      <Row gutter={[16,16]}>
        <Col xs={24} md={12}><Card loading={loading}><Statistic title="Portfolio Outstanding" value={par.total_portfolio || '0.00'} /></Card></Col>
        <Col xs={24} md={4}><Card loading={loading}><Statistic title="PAR30" value={par.par30 || '0.00'} /></Card></Col>
        <Col xs={24} md={4}><Card loading={loading}><Statistic title="PAR60" value={par.par60 || '0.00'} /></Card></Col>
        <Col xs={24} md={4}><Card loading={loading}><Statistic title="PAR90" value={par.par90 || '0.00'} /></Card></Col>
        <Col xs={24} md={6}><Card loading={loading}><Statistic title="PAR30 %" value={par.par30_pct || 0} suffix="%" /></Card></Col>
        <Col xs={24} md={6}><Card loading={loading}><Statistic title="PAR60 %" value={par.par60_pct || 0} suffix="%" /></Card></Col>
        <Col xs={24} md={6}><Card loading={loading}><Statistic title="PAR90 %" value={par.par90_pct || 0} suffix="%" /></Card></Col>
      </Row>

      <Card title="Filters" style={{ marginTop: 16 }}>
        <DatePicker onChange={setAsOf} placeholder="As of" style={{ marginRight: 12 }} />
        <span>Overdue threshold (days): </span>
        <input type="number" min={1} step={1} value={days} onChange={(e) => setDays(Number(e.target.value) || 30)} style={{ width: 80, marginLeft: 8 }} />
      </Card>

      <Row gutter={[16,16]} style={{ marginTop: 8 }}>
        <Col xs={24} md={12}>
          <Card title="PAR Buckets" loading={loading}>
            <Column data={parData} xField="bucket" yField="value" columnWidthRatio={0.5} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Top Overdue Installments" loading={loading}>
            <Table dataSource={overdue} columns={cols} rowKey={(r) => `${r.loan_id}-${r.installment_number}`} pagination={{ pageSize: 10 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default MicrofinanceDashboard;
