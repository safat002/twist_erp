import React, { useEffect, useState } from 'react';
import { Button, Card, DatePicker, Space, Statistic, message } from 'antd';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import { getVATReturn } from '../../../services/finance';

const VATReturn = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [range, setRange] = useState([dayjs().startOf('month'), dayjs().endOf('month')]);
  const [outputVAT, setOutputVAT] = useState(0);
  const [inputVAT, setInputVAT] = useState(0);
  const [net, setNet] = useState(0);

  const run = async () => {
    if (!range || !range[0] || !range[1]) return;
    try {
      setLoading(true);
      const params = { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') };
      const { data } = await getVATReturn(params);
      setOutputVAT(data?.output_vat || 0);
      setInputVAT(data?.input_vat || 0);
      setNet(data?.net_vat || 0);
    } catch (err) {
      message.error('Unable to load VAT return');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (currentCompany?.id) run(); }, [currentCompany?.id]);

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>VAT Return</span>
        <Space>
          <DatePicker.RangePicker value={range} onChange={setRange} />
          <Button type="primary" onClick={run} loading={loading}>Run</Button>
        </Space>
      </Space>
      <Space>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Output VAT (Sales)" value={outputVAT} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Input VAT (Purchases)" value={inputVAT} precision={2} />
        </Card>
        <Card bordered={false} style={{ minWidth: 220 }}>
          <Statistic title="Net VAT" value={net} precision={2} />
        </Card>
      </Space>
    </div>
  );
};

export default VATReturn;
