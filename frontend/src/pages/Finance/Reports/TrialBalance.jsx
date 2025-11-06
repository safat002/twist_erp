import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, DatePicker, Space, Statistic, Table, message } from 'antd';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import { getTrialBalance } from '../../../services/finance';

const TrialBalance = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [totals, setTotals] = useState({ debits: 0, credits: 0 });
  const [range, setRange] = useState([dayjs().startOf('month'), dayjs().endOf('month')]);

  const columns = useMemo(() => [
    { title: 'Code', dataIndex: 'code', key: 'code' },
    { title: 'Account', dataIndex: 'name', key: 'name' },
    { title: 'Type', dataIndex: 'type', key: 'type' },
    { title: 'Opening', dataIndex: 'opening', key: 'opening', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
    { title: 'Debits', dataIndex: 'debits', key: 'debits', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
    { title: 'Credits', dataIndex: 'credits', key: 'credits', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
    { title: 'Closing', dataIndex: 'closing', key: 'closing', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
  ], []);

  const load = async () => {
    if (!range || !range[0] || !range[1]) return;
    try {
      setLoading(true);
      const params = { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') };
      const { data } = await getTrialBalance(params);
      setRows(Array.isArray(data?.results) ? data.results : []);
      setTotals(data?.totals || { debits: 0, credits: 0 });
    } catch (err) {
      message.error('Unable to load trial balance');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (currentCompany?.id) load(); }, [currentCompany?.id]);

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>Trial Balance</span>
        <Space>
          <DatePicker.RangePicker value={range} onChange={setRange} />
          <Button type="primary" onClick={load}>Run</Button>
        </Space>
      </Space>
      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic title="Total Debits" value={totals?.debits || 0} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic title="Total Credits" value={totals?.credits || 0} precision={2} />
        </Card>
      </Space>
      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table rowKey={(r) => r.account_id} loading={loading} dataSource={rows} columns={columns} pagination={{ pageSize: 20 }} />
      </Card>
    </div>
  );
};

export default TrialBalance;
