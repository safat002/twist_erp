import React, { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Divider,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Upload,
  Spin,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  UploadOutlined,
  FileImageOutlined,
  FilePdfOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
  import {
    createJournalVoucher,
    deleteJournalVoucher,
    fetchAccounts,
    fetchJournalVouchers,
    fetchJournals,
    submitJournalVoucher,
    approveJournalVoucher,
    postJournalVoucher,
    updateJournalVoucher,
    processJournalVoucherDocument,
  } from '../../../services/finance';

const JournalVouchersList = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [journals, setJournals] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [vouchers, setVouchers] = useState([]);
  const [summary, setSummary] = useState({});
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedVoucher, setSelectedVoucher] = useState(null);
  const [editingVoucher, setEditingVoucher] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [processingDocument, setProcessingDocument] = useState(false);
  const [form] = Form.useForm();

  const loadLookups = async () => {
    try {
      const [{ data: journalData }, { data: accountData }] = await Promise.all([
        fetchJournals(),
        fetchAccounts(),
      ]);
      setJournals(Array.isArray(journalData?.results) ? journalData.results : journalData);
      setAccounts(Array.isArray(accountData?.results) ? accountData.results : []);
    } catch (error) {
      console.warn('Failed to load finance lookups', error?.message);
      message.error('Unable to load journals or accounts.');
    }
  };

  const loadVouchers = async () => {
    try {
      setLoading(true);
      const { data } = await fetchJournalVouchers();
      setVouchers(Array.isArray(data?.results) ? data.results : []);
      if (data?.summary) {
        setSummary(data.summary);
      }
    } catch (error) {
      console.warn('Failed to load vouchers', error?.message);
      message.error('Unable to load journal vouchers.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany?.id) {
      loadLookups();
      loadVouchers();
    }
  }, [currentCompany?.id]);

  const accountOptions = useMemo(
    () =>
      accounts.map((account) => ({
        value: account.id,
        label: `${account.code} · ${account.name}`,
      })),
    [accounts],
  );

  const handleCreate = () => {
    setEditingVoucher(null);
    setUploadedFile(null);
    form.resetFields();
    form.setFieldsValue({
      entry_date: dayjs(),
      status: 'DRAFT',
      entries: [
        { account: undefined, debit_amount: 0, credit_amount: 0, description: '' },
        { account: undefined, debit_amount: 0, credit_amount: 0, description: '' },
      ],
    });
    setModalVisible(true);
  };

  const handleFileUpload = async (file) => {
    setProcessingDocument(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const { data } = await processJournalVoucherDocument(formData);

      // Populate form with AI-extracted data
      const formValues = {
        entry_date: data.entry_date ? dayjs(data.entry_date) : dayjs(),
        status: 'DRAFT',
        reference: data.reference || '',
        description: data.description || '',
        entries: (data.entries || []).map((entry) => ({
          account: entry.account_id || undefined,
          debit_amount: entry.debit_amount || 0,
          credit_amount: entry.credit_amount || 0,
          description: entry.description || '',
        })),
      };

      if (data.journal_id) {
        formValues.journal = data.journal_id;
      }

      form.setFieldsValue(formValues);
      setUploadedFile(file);
      message.success('Document processed successfully! Please verify the extracted data.');
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Failed to process document.');
    } finally {
      setProcessingDocument(false);
    }
    return false; // Prevent default upload behavior
  };

  const handleEdit = (voucher) => {
    setEditingVoucher(voucher);
    form.setFieldsValue({
      journal: voucher.journal,
      entry_date: dayjs(voucher.entry_date),
      reference: voucher.reference,
      description: voucher.description,
      status: voucher.status,
      entries: (voucher.entries || []).map((entry) => ({
        account: entry.account,
        debit_amount: entry.debit_amount,
        credit_amount: entry.credit_amount,
        description: entry.description,
      })),
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    const payload = {
      ...values,
      entry_date: values.entry_date.format('YYYY-MM-DD'),
    };
    try {
      if (editingVoucher) {
        await updateJournalVoucher(editingVoucher.id, payload);
        message.success('Journal voucher updated.');
      } else {
        await createJournalVoucher(payload);
        message.success('Journal voucher created.');
      }
      setModalVisible(false);
      loadVouchers();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to save journal voucher.');
    }
  };

  const handleDelete = (voucher) => {
    Modal.confirm({
      title: `Delete ${voucher.voucher_number}?`,
      content: 'Deleting a voucher removes all entries. Continue?',
      okType: 'danger',
      onOk: async () => {
        try {
          await deleteJournalVoucher(voucher.id);
          message.success('Voucher deleted.');
          loadVouchers();
        } catch (error) {
          message.error(error?.response?.data?.detail || 'Unable to delete voucher.');
        }
      },
    });
  };

  const handlePost = async (voucher) => {
    try {
      await postJournalVoucher(voucher.id);
      message.success('Voucher posted successfully.');
      loadVouchers();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to post voucher.');
    }
  };

  const handleSubmitReview = async (voucher) => {
    try {
      await submitJournalVoucher(voucher.id);
      message.success('Voucher submitted for review.');
      loadVouchers();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to submit voucher.');
    }
  };

  const handleApprove = async (voucher) => {
    try {
      await approveJournalVoucher(voucher.id);
      message.success('Voucher approved and posted.');
      loadVouchers();
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to approve voucher.');
    }
  };

  const columns = [
    {
      title: 'Voucher #',
      dataIndex: 'voucher_number',
      key: 'voucher_number',
      render: (text, record) => (
        <Button type="link" onClick={() => setDrawerVisible(true) || setSelectedVoucher(record)}>
          {text}
        </Button>
      ),
    },
    {
      title: 'Journal',
      dataIndex: 'journal_name',
      key: 'journal',
    },
    {
      title: 'Date',
      dataIndex: 'entry_date',
      key: 'entry_date',
      render: (value) => dayjs(value).format('YYYY-MM-DD'),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'POSTED' ? 'green' : status === 'CANCELLED' ? 'red' : 'blue'}>
          {status}
        </Tag>
      ),
    },
    {
      title: 'Debit',
      dataIndex: 'total_debit',
      key: 'total_debit',
      align: 'right',
      render: (value) =>
        (Number(value || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      title: 'Credit',
      dataIndex: 'total_credit',
      key: 'total_credit',
      align: 'right',
      render: (value) =>
        (Number(value || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} type="text" onClick={() => handleEdit(record)} />
          {record.status === 'DRAFT' && (
            <>
              <Button type="link" onClick={() => handleSubmitReview(record)}>Submit</Button>
              <Button icon={<ThunderboltOutlined />} type="text" onClick={() => handlePost(record)}>
                Post
              </Button>
            </>
          )}
          {record.status === 'REVIEW' && (
            <Button type="link" onClick={() => handleApprove(record)}>Approve</Button>
          )}
          {record.status === 'POSTED' && (
            <Tag icon={<CheckCircleOutlined />} color="green">Posted</Tag>
          )}
          <Button
            icon={<DeleteOutlined />}
            danger
            type="text"
            onClick={() => handleDelete(record)}
          />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <FileTextOutlined style={{ fontSize: 24 }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>Journal Vouchers</span>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          New Voucher
        </Button>
      </Space>

      <Space style={{ marginBottom: 16 }}>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic title="Draft Vouchers" value={summary?.DRAFT || 0} />
        </Card>
        <Card bordered={false} style={{ minWidth: 200 }}>
          <Statistic title="Posted Vouchers" value={summary?.POSTED || 0} />
        </Card>
      </Space>

      <Card bordered={false} bodyStyle={{ padding: 0 }}>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={vouchers}
          columns={columns}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <Drawer
        width={560}
        title={selectedVoucher ? selectedVoucher.voucher_number : 'Voucher'}
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setSelectedVoucher(null);
        }}
      >
        {selectedVoucher ? (
          <>
            <p>
              <strong>Journal:</strong> {selectedVoucher.journal_name}
            </p>
            <p>
              <strong>Date:</strong> {dayjs(selectedVoucher.entry_date).format('YYYY-MM-DD')}
            </p>
            <p>
              <strong>Description:</strong> {selectedVoucher.description || '—'}
            </p>
            <Divider />
            <Table
              rowKey={(record) => `${record.account_detail?.id}-${record.line_number}`}
              dataSource={selectedVoucher.entries || []}
              pagination={false}
              columns={[
                {
                  title: 'Account',
                  dataIndex: ['account_detail', 'code'],
                  key: 'account',
                  render: (_, record) =>
                    `${record.account_detail?.code || ''} · ${record.account_detail?.name || ''}`,
                },
                {
                  title: 'Description',
                  dataIndex: 'description',
                  key: 'desc',
                },
                {
                  title: 'Debit',
                  dataIndex: 'debit_amount',
                  key: 'debit',
                  align: 'right',
                },
                {
                  title: 'Credit',
                  dataIndex: 'credit_amount',
                  key: 'credit',
                  align: 'right',
                },
              ]}
            />
          </>
        ) : null}
      </Drawer>

      <Modal
        title={editingVoucher ? 'Edit Journal Voucher' : 'Create Journal Voucher'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        destroyOnClose
        width={1400}
        onOk={() => form.submit()}
      >
        <Spin spinning={processingDocument} tip="Processing document with AI...">
          {!editingVoucher && (
            <div style={{ marginBottom: 16 }}>
              <Upload
                accept=".pdf,.jpg,.jpeg,.png"
                beforeUpload={handleFileUpload}
                showUploadList={false}
                maxCount={1}
              >
                <Button icon={<UploadOutlined />} type="dashed" block>
                  <FileImageOutlined /> <FilePdfOutlined /> Upload PDF/Image to Auto-Fill
                </Button>
              </Upload>
              {uploadedFile && (
                <div style={{ marginTop: 8, color: '#52c41a' }}>
                  <CheckCircleOutlined /> File uploaded: {uploadedFile.name}
                </div>
              )}
            </div>
          )}
          <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            name="journal"
            label="Journal"
            rules={[{ required: true, message: 'Select a journal' }]}
          >
            <Select
              options={journals.map((journal) => ({
                value: journal.id || journal,
                label: journal.name || journal,
              }))}
            />
          </Form.Item>
          <Space size="large" style={{ width: '100%' }}>
            <Form.Item
              name="entry_date"
              label="Entry Date"
              style={{ flex: 1 }}
              rules={[{ required: true, message: 'Select entry date' }]}
            >
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="status" label="Status" style={{ flex: 1 }}>
              <Select
                options={[
                  { label: 'Draft', value: 'DRAFT' },
                  { label: 'Post now', value: 'POSTED' },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item name="reference" label="Reference">
            <Input placeholder="Optional reference" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Narration for the voucher" />
          </Form.Item>
          <Divider orientation="left">Entries</Divider>
          <Form.List name="entries">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...field }) => (
                  <div
                    key={key}
                    style={{
                      display: 'flex',
                      gap: '8px',
                      marginBottom: 12,
                      alignItems: 'baseline',
                      flexWrap: 'nowrap'
                    }}
                  >
                    <Form.Item
                      {...field}
                      name={[name, 'account']}
                      rules={[{ required: true, message: 'Select account' }]}
                      style={{ flex: '0 0 450px', marginBottom: 0 }}
                    >
                      <Select
                        showSearch
                        placeholder="Select Account"
                        optionFilterProp="label"
                        options={accountOptions}
                      />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[name, 'debit_amount']}
                      initialValue={0}
                      style={{ flex: '0 0 140px', marginBottom: 0 }}
                    >
                      <Input placeholder="Debit" type="number" step="0.01" />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[name, 'credit_amount']}
                      initialValue={0}
                      style={{ flex: '0 0 140px', marginBottom: 0 }}
                    >
                      <Input placeholder="Credit" type="number" step="0.01" />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[name, 'description']}
                      style={{ flex: '1', marginBottom: 0 }}
                    >
                      <Input placeholder="Line description" />
                    </Form.Item>
                    {fields.length > 1 && (
                      <Button
                        type="text"
                        danger
                        onClick={() => remove(name)}
                        style={{ flex: '0 0 auto' }}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  Add Line
                </Button>
              </>
            )}
          </Form.List>
        </Form>
        </Spin>
      </Modal>
    </div>
  );
};

export default JournalVouchersList;
