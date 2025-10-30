import React, { useEffect, useMemo, useState } from 'react';
import { Card, Col, List, Row, Space, Statistic, Tag, Typography, message } from 'antd';
import {
  ApartmentOutlined,
  BankOutlined,
  FileSearchOutlined,
  FundOutlined,
  ShoppingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../contexts/CompanyContext';
import { fetchAccounts, fetchInvoices, fetchPayments } from '../../services/finance';

const { Title, Text } = Typography;

const FinanceWorkspace = () => {
  const { currentCompany } = useCompany();
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);

  const loadWorkspace = async () => {
    try {
      setLoading(true);
      const [{ data: accountData }, { data: invoiceData }, { data: paymentData }] = await Promise.all([
        fetchAccounts(),
        fetchInvoices(),
        fetchPayments(),
      ]);
      setAccounts(Array.isArray(accountData?.results) ? accountData.results : []);
      setInvoices(Array.isArray(invoiceData?.results) ? invoiceData.results : []);
      setPayments(Array.isArray(paymentData?.results) ? paymentData.results : []);
    } catch (error) {
      console.warn('Failed to load finance workspace', error?.message);
      message.error('Unable to load finance dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentCompany?.id) {
      loadWorkspace();
    }
  }, [currentCompany?.id]);

  const stats = useMemo(() => {
    const cashBalance = accounts
      .filter((account) => account.is_bank_account)
      .reduce((sum, account) => sum + Number(account.current_balance || 0), 0);

    const arOpen = invoices
      .filter((invoice) => invoice.invoice_type === 'AR')
      .reduce((sum, invoice) => sum + Number(invoice.balance_due || 0), 0);

    const apOpen = invoices
      .filter((invoice) => invoice.invoice_type === 'AP')
      .reduce((sum, invoice) => sum + Number(invoice.balance_due || 0), 0);

    const postedPayments = payments.filter((payment) => payment.status === 'POSTED').length;

    const overdueInvoices = invoices.filter(
      (invoice) => invoice.balance_due > 0 && dayjs(invoice.due_date).isBefore(dayjs(), 'day'),
    ).length;

    return { cashBalance, arOpen, apOpen, postedPayments, overdueInvoices };
  }, [accounts, invoices, payments]);

  const recentInvoices = useMemo(
    () =>
      invoices
        .slice(0, 5)
        .map((invoice) => ({
          id: invoice.id,
          number: invoice.invoice_number || 'Draft',
          type: invoice.invoice_type,
          amount: Number(invoice.total_amount || 0).toLocaleString(),
          status: invoice.status,
          due: dayjs(invoice.due_date).format('YYYY-MM-DD'),
        })),
    [invoices],
  );

  const recentPayments = useMemo(
    () =>
      payments
        .slice(0, 5)
        .map((payment) => ({
          id: payment.id,
          number: payment.payment_number || 'Draft',
          type: payment.payment_type,
          amount: Number(payment.amount || 0).toLocaleString(),
          status: payment.status,
          date: dayjs(payment.payment_date).format('YYYY-MM-DD'),
        })),
    [payments],
  );

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
          <Space>
            <FundOutlined style={{ fontSize: 28 }} />
            <div>
              <Title level={3} style={{ margin: 0 }}>
                Finance Control Tower
              </Title>
              <Text type="secondary">
                {currentCompany?.name} · Snapshot as of {dayjs().format('MMMM D, YYYY')}
              </Text>
            </div>
          </Space>
        </Space>

        <Row gutter={[16, 16]}>
          <Col xs={24} md={12} lg={6}>
            <Card loading={loading} bordered={false}>
              <Statistic
                title="Cash & Bank"
                prefix={<BankOutlined />}
                value={stats.cashBalance}
                precision={2}
              />
            </Card>
          </Col>
          <Col xs={24} md={12} lg={6}>
            <Card loading={loading} bordered={false}>
              <Statistic
                title="Accounts Receivable"
                prefix={<FileSearchOutlined />}
                value={stats.arOpen}
                precision={2}
              />
            </Card>
          </Col>
          <Col xs={24} md={12} lg={6}>
            <Card loading={loading} bordered={false}>
              <Statistic
                title="Accounts Payable"
                prefix={<ShoppingOutlined />}
                value={stats.apOpen}
                precision={2}
              />
            </Card>
          </Col>
          <Col xs={24} md={12} lg={6}>
            <Card loading={loading} bordered={false}>
              <Statistic
                title="Payments Posted"
                prefix={<ApartmentOutlined />}
                value={stats.postedPayments}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="Recent Invoices" loading={loading} bordered={false}>
              <List
                dataSource={recentInvoices}
                locale={{ emptyText: 'No invoices recorded yet.' }}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                        <Text strong>{item.number}</Text>
                        <Tag color={item.type === 'AR' ? 'blue' : 'volcano'}>{item.type}</Tag>
                      </Space>
                      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                        <Text type="secondary">Due {item.due}</Text>
                        <Tag color={item.status === 'PAID' ? 'green' : 'default'}>{item.status}</Tag>
                      </Space>
                      <Text>Amount: ৳ {item.amount}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Recent Payments" loading={loading} bordered={false}>
              <List
                dataSource={recentPayments}
                locale={{ emptyText: 'No payments recorded yet.' }}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" size={0} style={{ width: '100%' }}>
                      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                        <Text strong>{item.number}</Text>
                        <Tag color={item.type === 'RECEIPT' ? 'green' : 'volcano'}>{item.type}</Tag>
                      </Space>
                      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                        <Text type="secondary">{item.date}</Text>
                        <Tag color={item.status === 'POSTED' ? 'green' : 'default'}>{item.status}</Tag>
                      </Space>
                      <Text>Amount: ৳ {item.amount}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>

        <Card bordered={false} title="Alerts" loading={loading}>
          <List
            dataSource={[
              {
                id: 'overdue',
                message: `${stats.overdueInvoices} invoice(s) overdue. Follow up with customers immediately.`,
                severity: stats.overdueInvoices > 0 ? 'error' : 'success',
              },
              {
                id: 'cash-coverage',
                message:
                  stats.cashBalance < stats.apOpen
                    ? 'Cash balance is lower than outstanding payables.'
                    : 'Cash balance comfortably covers payables.',
                severity: stats.cashBalance < stats.apOpen ? 'warning' : 'success',
              },
            ]}
            renderItem={(alert) => (
              <List.Item>
                <Tag color={alert.severity === 'error' ? 'red' : alert.severity === 'warning' ? 'orange' : 'green'}>
                  {alert.severity.toUpperCase()}
                </Tag>
                <Text style={{ marginLeft: 8 }}>{alert.message}</Text>
              </List.Item>
            )}
          />
        </Card>
      </Space>
    </div>
  );
};

export default FinanceWorkspace;
