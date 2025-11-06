import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, DatePicker, Select, Space, Statistic, Table, message } from 'antd';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import { fetchAccounts, getGeneralLedger } from '../../../services/finance';

const GeneralLedger = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [accountId, setAccountId] = useState(null);
  const [opening, setOpening] = useState(0);
  const [lines, setLines] = useState([]);
  const [range, setRange] = useState([dayjs().startOf('month'), dayjs().endOf('month')]);

  const accountOptions = useMemo(
    () => accounts.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` })),
    [accounts]
  );

  const columns = useMemo(() => [
    { title: 'Date', dataIndex: 'date', key: 'date' },
    { title: 'Voucher', dataIndex: 'voucher', key: 'voucher' },
    { title: 'Reference', dataIndex: 'ref', key: 'ref' },
    { title: 'Description', dataIndex: 'desc', key: 'desc' },
    { title: 'Debit', dataIndex: 'debit', key: 'debit', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
    { title: 'Credit', dataIndex: 'credit', key: 'credit', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
    { title: 'Balance', dataIndex: 'balance', key: 'balance', align: 'right', render: (v) => (Number(v || 0)).toLocaleString() },
  ], []);

  const loadAccounts = async () => {
    try {
      const { data } = await fetchAccounts();
      setAccounts(Array.isArray(data?.results) ? data.results : []);
    } catch (err) {
      message.error('Unable to load accounts');
    }
  };

  const load = async () => {
    if (!accountId || !range || !range[0] || !range[1]) return;
    try {
      setLoading(true);
      const params = {
        account: accountId,
        start: range[0].format('YYYY-MM-DD'),
        end: range[1].format('YYYY-MM-DD'),
      };
      const { data } = await getGeneralLedger(params);
      setOpening(data?.opening || 0);
      setLines(Array.isArray(data?.lines) ? data.lines : []);
    } catch (err) {
      message.error('Unable to load general ledger');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (currentCompany?.id) loadAccounts(); }, [currentCompany?.id]);

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>General Ledger</span>
        <Space>
          <Select
            showSearch
            placeholder="Select account"
            options={accountOptions}
            value={accountId}
            onChange={setAccountId}
            style={{ width: 360 }}
            optionFilterProp="label"
          />
          <DatePicker.RangePicker value={range} onChange={setRange} />
          <Button type="primary" onClick={load}>Run</Button>
        </Space>
      </Space>
      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Opening Balance" value={opening || 0} precision={2} />
        </Card>
      </Space>
      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table rowKey={(r, i) => `${r.voucher}-${i}`} loading={loading} dataSource={lines} columns={columns} pagination={{ pageSize: 25 }} />
      </Card>
    </div>
  );
};

export default GeneralLedger;
