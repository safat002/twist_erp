import React, { useEffect, useMemo, useState } from 'react';
import { Card, Row, Col, Select, Table, Button, Modal, Form, Input, DatePicker, Upload, Space } from 'antd';
import { App as AntApp } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import api from '../../services/api';
import usePermissions from '../../hooks/usePermissions';

const Compliance = () => {
  const [programs, setPrograms] = useState([]);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [requirements, setRequirements] = useState([]);
  const [selectedReq, setSelectedReq] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reqOpen, setReqOpen] = useState(false);
  const [subOpen, setSubOpen] = useState(false);
  const [reqForm] = Form.useForm();
  const [subForm] = Form.useForm();
  const { can } = usePermissions();
  const { message } = AntApp.useApp();

  const loadPrograms = async () => {
    try {
      const res = await api.get('/api/v1/ngo/programs/');
      const list = Array.isArray(res.data) ? res.data : res.data?.results || [];
      setPrograms(list.map((p) => ({ value: p.id, label: `${p.code} - ${p.title}` })));
    } catch (e) {
      message.error('Failed to load programs');
    }
  };

  const loadRequirements = async (programId) => {
    setLoading(true);
    try {
      const res = await api.get('/api/v1/ngo/requirements/', { params: { program: programId } }).catch(() => api.get('/api/v1/ngo/requirements/'));
      const list = Array.isArray(res.data) ? res.data : res.data?.results || [];
      const filtered = list.filter((r) => r.program === programId || selectedProgram === programId);
      setRequirements(filtered);
    } catch (e) {
      setRequirements([]);
    } finally {
      setLoading(false);
    }
  };

  const loadSubmissions = async (reqId) => {
    setLoading(true);
    try {
      const res = await api.get('/api/v1/ngo/submissions/', { params: { requirement: reqId } }).catch(() => api.get('/api/v1/ngo/submissions/'));
      const list = Array.isArray(res.data) ? res.data : res.data?.results || [];
      const filtered = list.filter((s) => s.requirement === reqId);
      setSubmissions(filtered);
    } catch (e) {
      setSubmissions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadPrograms(); }, []);
  useEffect(() => { if (selectedProgram) loadRequirements(selectedProgram); }, [selectedProgram]);
  useEffect(() => { if (selectedReq) loadSubmissions(selectedReq); }, [selectedReq]);

  const reqCols = useMemo(() => ([
    { title: 'Code', dataIndex: 'code' },
    { title: 'Name', dataIndex: 'name' },
    { title: 'Frequency', dataIndex: 'frequency' },
    { title: 'Next Due', dataIndex: 'next_due_date' },
    {
      title: 'Actions', key: 'actions', render: (_, r) => (
        <Space>
          <Button size="small" onClick={() => setSelectedReq(r.id)}>View Submissions</Button>
          {can('ngo.update_program') && (
            <Button size="small" type="primary" onClick={() => openSubmission(r.id)}>Add Submission</Button>
          )}
        </Space>
      ),
    },
  ]), [can]);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  const subCols = useMemo(() => ([
    { title: 'Period', dataIndex: 'period_start', render: (_, r) => `${r.period_start || ''} → ${r.period_end || ''}` },
    { title: 'Submitted', dataIndex: 'submitted_at' },
    { title: 'Status', dataIndex: 'status' },
    { title: 'File', dataIndex: 'file', render: (v, r) => v ? (
      <Space>
        <Button size="small" onClick={() => window.open(v, '_blank')}>Open</Button>
        <Button size="small" onClick={() => { setPreviewUrl(v); setPreviewOpen(true); }}>Preview</Button>
      </Space>
    ) : '' },
  ]), []);

  const createRequirement = async () => {
    try {
      const v = await reqForm.validateFields();
      await api.post('/api/v1/ngo/requirements/', {
        program: selectedProgram,
        code: v.code,
        name: v.name,
        frequency: v.frequency,
        next_due_date: v.next_due_date?.format('YYYY-MM-DD'),
      });
      setReqOpen(false);
      reqForm.resetFields();
      loadRequirements(selectedProgram);
      message.success('Requirement created');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to create requirement');
    }
  };

  const openSubmission = (reqId) => {
    setSelectedReq(reqId);
    setSubOpen(true);
  };

  const createSubmission = async () => {
    try {
      const v = await subForm.validateFields();
      const fd = new FormData();
      fd.append('requirement', selectedReq);
      if (v.period_start) fd.append('period_start', v.period_start.format('YYYY-MM-DD'));
      if (v.period_end) fd.append('period_end', v.period_end.format('YYYY-MM-DD'));
      if (v.file && v.file.file) fd.append('file', v.file.file);
      await api.post('/api/v1/ngo/submissions/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setSubOpen(false);
      subForm.resetFields();
      loadSubmissions(selectedReq);
      message.success('Submission added');
    } catch (e) {
      if (e?.errorFields) return;
      message.error('Failed to add submission');
    }
  };

  return (
    <Row gutter={16}>
      <Col span={24}>
        <Card title="Compliance Management"
          extra={can('ngo.update_program') && selectedProgram ? <Button onClick={() => setReqOpen(true)}>New Requirement</Button> : null}
        >
          <Space style={{ marginBottom: 12 }}>
            <Select options={programs} style={{ minWidth: 320 }} placeholder="Select Program" value={selectedProgram} onChange={setSelectedProgram} />
          </Space>
          <Table dataSource={requirements} columns={reqCols} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
          {selectedReq && (
            <Card title="Submissions" style={{ marginTop: 16 }}>
              <Table dataSource={submissions} columns={subCols} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
            </Card>
          )}
        </Card>
      </Col>

      <Modal title="New Requirement" open={reqOpen} onCancel={() => setReqOpen(false)} onOk={createRequirement} okText="Create">
        <Form layout="vertical" form={reqForm}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="frequency" label="Frequency" initialValue="quarterly" rules={[{ required: true }]}>
            <Select options={[{value:'once',label:'Once'},{value:'monthly',label:'Monthly'},{value:'quarterly',label:'Quarterly'},{value:'annual',label:'Annual'}]} />
          </Form.Item>
          <Form.Item name="next_due_date" label="Next Due"><DatePicker style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="New Submission" open={subOpen} onCancel={() => setSubOpen(false)} onOk={createSubmission} okText="Submit">
        <Form layout="vertical" form={subForm}>
          <Form.Item name="period_start" label="Period Start"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="period_end" label="Period End"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="file" label="Attachment"><Upload beforeUpload={() => false} maxCount={1}><Button icon={<UploadOutlined />}>Select File</Button></Upload></Form.Item>
        </Form>
      </Modal>
      <Modal title="Preview" open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={900}>
        {previewUrl ? <iframe title="preview" src={previewUrl} style={{ width: '100%', height: '70vh', border: 0 }} /> : 'No file'}
      </Modal>
    </Row>
  );
};

export default Compliance;
