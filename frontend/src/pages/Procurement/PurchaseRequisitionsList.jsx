import React, { useEffect, useMemo, useState } from 'react';
import { Card, DatePicker, Space, Table, Tag, Typography, Select, Button, message, Drawer } from 'antd';
import dayjs from 'dayjs';
import api from '../../services/api';
import { useLocation } from 'react-router-dom';

const { Title, Text } = Typography;

const PurchaseRequisitionsList = () => {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateRange, setDateRange] = useState([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState(null);
  const location = useLocation();

  const load = async () => {
    try {
      setLoading(true);
      const params = {};
      if (statusFilter && statusFilter !== 'ALL') params.status = statusFilter;
      const { data } = await api.get('/api/v1/procurement/purchase-requisitions/', { params });
      const list = Array.isArray(data) ? data : data?.results || [];
      setRows(list);
    } catch (e) {
      message.error('Unable to load Purchase Requisitions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [statusFilter]);

  useEffect(() => {
    // Auto-open drawer if query param 'open' provided (number or id)
    const qs = new URLSearchParams(location.search || '');
    const openKey = qs.get('open');
    if (openKey && Array.isArray(rows) && rows.length > 0) {
      const found = rows.find((r) => String(r.requisition_number) === String(openKey) || String(r.id) === String(openKey));
      if (found) {
        openDetail(found.id);
      }
    }
  }, [location.search, rows]);

  const filtered = useMemo(() => {
    let list = Array.isArray(rows) ? rows : [];
    if (Array.isArray(dateRange) && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
      const [start, end] = dateRange;
      list = list.filter((r) => {
        const d = r.submitted_at || r.created_at;
        const m = d ? dayjs(d) : null;
        return m && m.isAfter(start.startOf('day')) && m.isBefore(end.endOf('day'));
      });
    }
    return list;
  }, [rows, dateRange]);

  const columns = [
    { title: 'PR No', dataIndex: 'requisition_number', key: 'requisition_number' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s) => <Tag>{s}</Tag> },
    { title: 'Priority', dataIndex: 'priority', key: 'priority' },
    { title: 'Request Type', dataIndex: 'request_type', key: 'request_type' },
    { title: 'Required By', dataIndex: 'required_by', key: 'required_by', render: (v) => (v ? dayjs(v).format('YYYY-MM-DD') : '-') },
    { title: 'Total Qty', dataIndex: 'total_estimated_quantity', key: 'total_estimated_quantity' },
    { title: 'Total Value', dataIndex: 'total_estimated_value', key: 'total_estimated_value' },
    { title: 'Cost Center', dataIndex: ['cost_center','name'], key: 'cost_center', render: (_v, r) => r?.cost_center?.name || '-' },
    { title: 'Actions', key: 'actions', render: (_v, r) => (<Button size="small" onClick={() => openDetail(r.id)}>View</Button>) },
  ];

  const exportCsv = () => {
    const header = 'PR No,Status,Priority,Request Type,Required By,Total Qty,Total Value,Cost Center\n';
    const body = filtered.map((r) => (
      `${r.requisition_number},${r.status},${r.priority},${r.request_type},${r.required_by || ''},${r.total_estimated_quantity || 0},${r.total_estimated_value || 0},"${(r?.cost_center?.name || '').replace(/"/g,'""')}"`
    )).join('\n');
    const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'purchase_requisitions.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const openDetail = async (id) => {
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const { data } = await api.get(`/api/v1/procurement/purchase-requisitions/${id}/`);
      setDetail(data);
    } catch (e) {
      message.error('Unable to load details');
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div>
      <Title level={2}>Purchase Requisitions</Title>
      <Text type="secondary">Read-only list of submitted Purchase Requisitions.</Text>
      <Card style={{ marginTop: 16 }}
        extra={(
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'ALL', label: 'All' },
                { value: 'draft', label: 'Draft' },
                { value: 'submitted', label: 'Submitted' },
                { value: 'under_review', label: 'Under Review' },
                { value: 'approved', label: 'Approved' },
                { value: 'rejected', label: 'Rejected' },
                { value: 'cancelled', label: 'Cancelled' },
                { value: 'converted', label: 'Converted to PO' },
              ]}
              style={{ width: 220 }}
            />
            <DatePicker.RangePicker onChange={setDateRange} />
            <Button onClick={exportCsv}>Export CSV</Button>
          </Space>
        )}
      >
        <Table rowKey={(r) => r.id} loading={loading} dataSource={filtered} columns={columns} pagination={{ pageSize: 10 }} />
      </Card>

      <Drawer
        title={detail?.requisition_number ? `PR ${detail.requisition_number}` : 'Purchase Requisition'}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={900}
      >
        {detailLoading ? (
          <div>Loading...</div>
        ) : detail ? (
          <div>
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <div>
                <Text strong>Status: </Text><Tag>{detail.status}</Tag>
              </div>
              <div>
                <Text strong>Priority: </Text>{detail.priority || '-'} &nbsp; | &nbsp;
                <Text strong>Request Type: </Text>{detail.request_type || '-'}
              </div>
              <div>
                <Text strong>Required By: </Text>{detail.required_by || '-'} &nbsp; | &nbsp;
                <Text strong>Cost Center: </Text>{detail?.cost_center?.name || '-'}
              </div>
              <div>
                <Text strong>Total Qty: </Text>{detail.total_estimated_quantity || 0} &nbsp; | &nbsp;
                <Text strong>Total Value: </Text>{detail.total_estimated_value || 0}
              </div>
              <Card size="small" title="Lines">
                <Table
                  size="small"
                  rowKey={(r) => r.id}
                  dataSource={detail.lines || []}
                  columns={[
                    { title: '#', dataIndex: 'line_number', key: 'line_number', width: 60 },
                    { title: 'Budget Line', dataIndex: ['budget_line','id'], key: 'budget_line', render: (_v, r) => r?.budget_line || r?.budget_line_name || '-' },
                    { title: 'Description', dataIndex: 'description', key: 'description' },
                    { title: 'Product', dataIndex: ['product','name'], key: 'product', render: (_v, r) => r?.product?.name || '-' },
                    { title: 'Qty', dataIndex: 'quantity', key: 'quantity', width: 100 },
                    { title: 'UoM', dataIndex: ['uom','name'], key: 'uom', render: (_v, r) => r?.uom?.name || '-' },
                    { title: 'Est. Unit Cost', dataIndex: 'estimated_unit_cost', key: 'estimated_unit_cost', width: 140 },
                    { title: 'Est. Total', dataIndex: 'estimated_total_cost', key: 'estimated_total_cost', width: 140 },
                  ]}
                  pagination={false}
                />
              </Card>
            </Space>
          </div>
        ) : (
          <div>No data</div>
        )}
      </Drawer>
    </div>
  );
};

export default PurchaseRequisitionsList;
