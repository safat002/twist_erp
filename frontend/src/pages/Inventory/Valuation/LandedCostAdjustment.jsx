import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Card, Row, Col, Select, InputNumber, Input, Button, Typography, Space, message, Table, Tag } from 'antd';
import { DollarOutlined, FileSearchOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useCompany } from '../../../contexts/CompanyContext';
import valuationService from '../../../services/valuation';

const { Title, Text } = Typography;

const LandedCostAdjustment = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [grns, setGrns] = useState([]);
  const [selectedGrnId, setSelectedGrnId] = useState(null);
  const [adjustment, setAdjustment] = useState(0);
  const [method, setMethod] = useState('QUANTITY');
  const [reason, setReason] = useState('Freight/Import charges');
  const [result, setResult] = useState(null);

  const loadGrns = useCallback(async () => {
    setLoading(true);
    try {
      const items = await valuationService.getGoodsReceipts({ status: 'POSTED' });
      setGrns(items);
    } catch (err) {
      console.error(err);
      message.error('Failed to load Goods Receipts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentCompany) loadGrns();
  }, [currentCompany, loadGrns]);

  const grnOptions = useMemo(() => (grns || []).map(g => ({
    value: g.id,
    label: `${g.receipt_number || 'GRN-' + g.id} | ${g.supplier?.name || 'Supplier'} | ${g.receipt_date}`,
  })), [grns]);

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: 'GRN', dataIndex: 'receipt_number', key: 'receipt_number' },
    { title: 'Supplier', dataIndex: ['supplier', 'name'], key: 'supplier' },
    { title: 'Date', dataIndex: 'receipt_date', key: 'receipt_date' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: v => <Tag color={v === 'POSTED' ? 'green' : 'blue'}>{v}</Tag> },
  ];

  const handleApply = async () => {
    if (!selectedGrnId) {
      message.warning('Please select a posted Goods Receipt');
      return;
    }
    if (!adjustment || Number(adjustment) <= 0) {
      message.warning('Enter a positive adjustment amount');
      return;
    }
    try {
      setLoading(true);
      const res = await valuationService.applyLandedCostAdjustment(selectedGrnId, Number(adjustment), method, reason);
      setResult(res);
      message.success('Landed cost adjustment applied');
      await loadGrns();
    } catch (err) {
      console.error(err);
      message.error(err?.response?.data?.error || 'Failed to apply landed cost adjustment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={2} style={{ marginBottom: 0 }}>Landed Cost Adjustment</Title>
          <Text type="secondary">Apportion freight/duty across a posted GRN and update valuation</Text>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={14}>
          <Card title={<Space><FileSearchOutlined /> Select Goods Receipt</Space>} loading={loading}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Select
                showSearch
                placeholder="Choose a posted GRN"
                options={grnOptions}
                value={selectedGrnId}
                onChange={setSelectedGrnId}
                filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
              />
              <Table
                size="small"
                columns={columns}
                dataSource={grns}
                rowKey="id"
                pagination={{ pageSize: 5 }}
                onRow={(record) => ({ onClick: () => setSelectedGrnId(record.id) })}
              />
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={10}>
          <Card title={<Space><DollarOutlined /> Adjustment</Space>}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text strong>Total Adjustment</Text>
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  step={0.01}
                  precision={2}
                  value={adjustment}
                  onChange={setAdjustment}
                />
              </div>
              <div>
                <Text strong>Apportion By</Text>
                <Select
                  style={{ width: '100%' }}
                  value={method}
                  onChange={setMethod}
                  options={[{ value: 'QUANTITY', label: 'Quantity' }, { value: 'VALUE', label: 'Value' }]}
                />
              </div>
              <div>
                <Text strong>Reason</Text>
                <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Freight / Insurance / Duty" />
              </div>
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleApply} loading={loading}>
                Apply Adjustment
              </Button>
              {result && (
                <Card size="small" type="inner" title="Result">
                  <Space direction="vertical">
                    <Text>Inventory adjusted: <Text strong>{Number(result.inventory_adjustment || 0).toFixed(2)}</Text></Text>
                    <Text>COGS adjusted: <Text strong>{Number(result.consumed_adjustment || 0).toFixed(2)}</Text></Text>
                    <Text type="secondary">Credit: Accrued Freight</Text>
                  </Space>
                </Card>
              )}
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default LandedCostAdjustment;

