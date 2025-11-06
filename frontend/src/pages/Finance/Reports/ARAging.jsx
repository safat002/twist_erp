import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, DatePicker, Space, Statistic, Table, Tabs, message } from 'antd';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import { getARAging } from '../../../services/finance';

const ARAging = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [asOf, setAsOf] = useState(dayjs());
  const [summary, setSummary] = useState({});
  const [buckets, setBuckets] = useState({});

  const columns = useMemo(() => [
    { title: 'Invoice', dataIndex: 'number', key: 'number' },
    { title: 'Partner', dataIndex: 'partner_id', key: 'partner' },
    { title: 'Due Date', dataIndex: 'due_date', key: 'due' },
    { title: 'Amount', dataIndex: 'amount', key: 'amount', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
  ], []);

  const load = async () => {
    try {
      setLoading(true);
      const { data } = await getARAging({ as_of: asOf.format('YYYY-MM-DD') });
      setSummary(data?.summary || {});
      setBuckets(data?.buckets || {});
    } catch (err) {
      message.error('Unable to load AR aging');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (currentCompany?.id) load(); }, [currentCompany?.id]);

  const renderBucket = (key, title) => (
    <Table
      rowKey={(r) => r.id}
      loading={loading}
      dataSource={Array.isArray(buckets[key]) ? buckets[key] : []}
      columns={columns}
      pagination={{ pageSize: 10 }}
    />
  );

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>AR Aging</span>
        <Space>
          <DatePicker value={asOf} onChange={setAsOf} />
          <Button type="primary" onClick={load}>Run</Button>
        </Space>
      </Space>
      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 180 }}>
          <Statistic title="Current" value={summary?.CURRENT || 0} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 180 }}>
          <Statistic title="1–30" value={summary?.DUE_1_30 || 0} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 180 }}>
          <Statistic title="31–60" value={summary?.DUE_31_60 || 0} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 180 }}>
          <Statistic title="61–90" value={summary?.DUE_61_90 || 0} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 180 }}>
          <Statistic title=">90" value={summary?.[">90"] || 0} precision={2} />
        </Card>
      </Space>
      <Tabs
        items={[
          { key: 'CURRENT', label: 'Current', children: renderBucket('CURRENT') },
          { key: 'DUE_1_30', label: '1–30', children: renderBucket('DUE_1_30') },
          { key: 'DUE_31_60', label: '31–60', children: renderBucket('DUE_31_60') },
          { key: 'DUE_61_90', label: '61–90', children: renderBucket('DUE_61_90') },
          { key: '>90', label: '>90', children: renderBucket('>90') },
        ]}
      />
    </div>
  );
};

export default ARAging;
