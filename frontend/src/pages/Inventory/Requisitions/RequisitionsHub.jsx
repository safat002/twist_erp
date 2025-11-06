import React, { useEffect, useMemo, useState } from 'react';
import { Tabs, Empty, Space, Dropdown, Button, Typography, Row, Col, Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, PlusOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useFeatures } from '../../../contexts/FeatureContext';
import InternalRequisitions from './InternalRequisitions';
import PurchaseRequisitions from './PurchaseRequisitions';
import api from '../../../services/api';

const RequisitionsHub = () => {
  const { isFeatureEnabled, refreshFeatures, loading: featuresLoading } = useFeatures();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { Title } = Typography;

  const canInternal = isFeatureEnabled('inventory', 'requisitions_internal');
  const canPurchase = isFeatureEnabled('inventory', 'purchase_requisitions');
  // Dev-friendly signal
  try {
    console.debug('RequisitionsHub flags', { canInternal, canPurchase });
    console.log('RequisitionsHub flags', { canInternal, canPurchase });
  } catch (_) {}
  const [loadingKpis, setLoadingKpis] = useState(false);
  const [kpis, setKpis] = useState({
    internal: { draft: 0, submitted: 0, approved: 0, cancelled: 0 },
    draft: { draft: 0, submitted: 0 },
    pr: { submitted: 0, approved: 0, under_review: 0, rejected: 0, cancelled: 0, converted: 0 },
  });
  const [trends, setTrends] = useState({
    internal: { draft: 0, submitted: 0, approved: 0, cancelled: 0 },
    draft: { draft: 0, submitted: 0 },
    pr: { submitted: 0, approved: 0, under_review: 0, rejected: 0, cancelled: 0, converted: 0 },
  });
  useLoadRequisitionKpis(canInternal, canPurchase, setLoadingKpis, setKpis, setTrends);

  const trendProps = (delta, polarity = 'positive') => {
    // polarity: 'positive' (more is good), 'negative' (more is bad), 'neutral'
    if (!delta) return { prefix: <MinusOutlined />, valueStyle: { color: '#8c8c8c' } };
    const good = delta > 0;
    if (polarity === 'negative') {
      // Increase is bad (red), decrease is good (green)
      return good
        ? { prefix: <ArrowUpOutlined />, valueStyle: { color: '#ff4d4f' } }
        : { prefix: <ArrowDownOutlined />, valueStyle: { color: '#52c41a' } };
    }
    if (polarity === 'neutral') {
      return good
        ? { prefix: <ArrowUpOutlined />, valueStyle: { color: '#1890ff' } }
        : { prefix: <ArrowDownOutlined />, valueStyle: { color: '#1890ff' } };
    }
    // positive
    return good
      ? { prefix: <ArrowUpOutlined />, valueStyle: { color: '#52c41a' } }
      : { prefix: <ArrowDownOutlined />, valueStyle: { color: '#ff4d4f' } };
  };

  // Creation drawer controls for child tabs
  const [openInternalNew, setOpenInternalNew] = useState(false);
  const [openPurchaseNew, setOpenPurchaseNew] = useState(false);

  const items = useMemo(() => {
    const tabs = [];
    if (canInternal) {
      tabs.push({ key: 'internal', label: 'Internal', children: <InternalRequisitions openNew={openInternalNew} onCloseNew={() => setOpenInternalNew(false)} /> });
    }
    if (canPurchase) {
      tabs.push({ key: 'purchase', label: 'Purchase', children: <PurchaseRequisitions openNew={openPurchaseNew} onCloseNew={() => setOpenPurchaseNew(false)} /> });
    }
    return tabs;
  }, [canInternal, canPurchase, openInternalNew, openPurchaseNew]);

  if (!items.length) {
    const itemsMenu = [];
    if (canInternal) itemsMenu.push({ key: 'internal', label: 'Internal Requisition' });
    if (canPurchase) itemsMenu.push({ key: 'purchase', label: 'Purchase Requisition' });
    return (
      <Card>
        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
          <Title level={3} style={{ margin: 0 }}>Requisitions</Title>
          <Dropdown.Button
            type="primary"
            icon={<PlusOutlined />}
            menu={{ items: itemsMenu, onClick: ({ key }) => {
              if (key === 'internal') setOpenInternalNew(true);
              if (key === 'purchase') setOpenPurchaseNew(true);
            }}}
            onClick={() => {
              if (canInternal) setOpenInternalNew(true);
              else if (canPurchase) setOpenPurchaseNew(true);
            }}
            disabled={!itemsMenu.length && !featuresLoading}
          >
            Make Requisition
          </Dropdown.Button>
        </Space>
        <Empty description="No requisition features enabled for this company." />
        <div style={{ marginTop: 12 }}>
          <Button onClick={() => refreshFeatures()}>Refresh Feature Flags</Button>
        </div>
      </Card>
    );
  }

  const qpTab = searchParams.get('tab');
  const defaultActiveKey = (qpTab === 'internal' || qpTab === 'purchase')
    ? qpTab
    : (canInternal ? 'internal' : (canPurchase ? 'purchase' : null));
  const [activeKey, setActiveKey] = useState(defaultActiveKey || 'internal');

   const menuItems = [];
   if (canInternal) {
     menuItems.push({ key: 'internal', label: 'Internal Requisition' });
   }
   if (canPurchase) {
     menuItems.push({ key: 'purchase', label: 'Purchase Requisition' });
   }

   const onNewClick = ({ key }) => {
     if (key === 'internal') {
       setActiveKey('internal');
       setOpenInternalNew(true);
     }
     if (key === 'purchase') {
       setActiveKey('purchase');
       setOpenPurchaseNew(true);
     }
   };

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
        <Title level={3} style={{ margin: 0 }}>Requisitions</Title>
        <Dropdown.Button
          type="primary"
          icon={<PlusOutlined />}
          menu={{ items: menuItems, onClick: onNewClick }}
          onClick={() => {
            // Primary button prefers Internal if available, else Purchase
            if (canInternal) {
              setActiveKey('internal');
              setOpenInternalNew(true);
            } else if (canPurchase) {
              setActiveKey('purchase');
              setOpenPurchaseNew(true);
            }
          }}
          disabled={!menuItems.length && !featuresLoading}
        >
          Make Requisition
        </Dropdown.Button>
      </Space>
      {/* KPI Row */}
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        {canInternal && (
          <>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="Internal Draft" value={kpis.internal.draft} {...trendProps(trends.internal.draft, 'neutral')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="Internal Submitted" value={kpis.internal.submitted} {...trendProps(trends.internal.submitted, 'positive')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="Internal Approved" value={kpis.internal.approved} {...trendProps(trends.internal.approved, 'positive')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="Internal Cancelled" value={kpis.internal.cancelled} {...trendProps(trends.internal.cancelled, 'negative')} />
              </Card>
            </Col>
          </>
        )}
        {canPurchase && (
          <>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Drafts" value={kpis.draft.draft} {...trendProps(trends.draft.draft, 'neutral')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Drafts Submitted" value={kpis.draft.submitted} {...trendProps(trends.draft.submitted, 'positive')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Approved" value={kpis.pr.approved} {...trendProps(trends.pr.approved, 'positive')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Submitted" value={kpis.pr.submitted} {...trendProps(trends.pr.submitted, 'positive')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Under Review" value={kpis.pr.under_review} {...trendProps(trends.pr.under_review, 'neutral')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Rejected" value={kpis.pr.rejected} {...trendProps(trends.pr.rejected, 'negative')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Cancelled" value={kpis.pr.cancelled} {...trendProps(trends.pr.cancelled, 'negative')} />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Card size="small" loading={loadingKpis}>
                <Statistic title="PR Converted" value={kpis.pr.converted} {...trendProps(trends.pr.converted, 'positive')} />
              </Card>
            </Col>
          </>
        )}
      </Row>
      <Tabs activeKey={activeKey} onChange={setActiveKey} items={items} />
    </div>
  );
};

async function fetchCount(url, params = {}) {
  try {
    const { data } = await api.get(url, { params });
    if (Array.isArray(data)) return data.length;
    if (Array.isArray(data?.results)) return data.results.length;
    if (typeof data?.count === 'number') return data.count;
    return 0;
  } catch (_e) {
    return 0;
  }
}

// Load KPIs

export const useLoadRequisitionKpis = (canInternal, canPurchase, setLoading, setKpis, setTrends) => {
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      const next = {
        internal: { draft: 0, submitted: 0, approved: 0, cancelled: 0 },
        draft: { draft: 0, submitted: 0 },
        pr: { submitted: 0, approved: 0, under_review: 0, rejected: 0, cancelled: 0, converted: 0 },
      };
      try {
        const promises = [];
        if (canInternal) {
          promises.push(
            fetchCount('/api/v1/inventory/requisitions/internal/', { status: 'DRAFT' }).then((v) => (next.internal.draft = v)),
            fetchCount('/api/v1/inventory/requisitions/internal/', { status: 'SUBMITTED' }).then((v) => (next.internal.submitted = v)),
            fetchCount('/api/v1/inventory/requisitions/internal/', { status: 'APPROVED' }).then((v) => (next.internal.approved = v)),
            fetchCount('/api/v1/inventory/requisitions/internal/', { status: 'CANCELLED' }).then((v) => (next.internal.cancelled = v)),
          );
        }
        if (canPurchase) {
          // Draft PRs (uppercase statuses in drafts)
          promises.push(
            fetchCount('/api/v1/procurement/requisitions/', { status: 'DRAFT' }).then((v) => (next.draft.draft = v)),
            fetchCount('/api/v1/procurement/requisitions/', { status: 'SUBMITTED' }).then((v) => (next.draft.submitted = v)),
          );
          // Full PRs (lowercase statuses)
          promises.push(
            fetchCount('/api/v1/procurement/purchase-requisitions/', { status: 'approved' }).then((v) => (next.pr.approved = v)),
            fetchCount('/api/v1/procurement/purchase-requisitions/', { status: 'submitted' }).then((v) => (next.pr.submitted = v)),
            fetchCount('/api/v1/procurement/purchase-requisitions/', { status: 'under_review' }).then((v) => (next.pr.under_review = v)),
            fetchCount('/api/v1/procurement/purchase-requisitions/', { status: 'rejected' }).then((v) => (next.pr.rejected = v)),
            fetchCount('/api/v1/procurement/purchase-requisitions/', { status: 'cancelled' }).then((v) => (next.pr.cancelled = v)),
            fetchCount('/api/v1/procurement/purchase-requisitions/', { status: 'converted' }).then((v) => (next.pr.converted = v)),
          );
        }
        await Promise.all(promises);
        if (!cancelled) {
          setKpis(prev => {
            const deltas = {
              internal: {
                draft: next.internal.draft - (prev.internal?.draft || 0),
                submitted: next.internal.submitted - (prev.internal?.submitted || 0),
                approved: next.internal.approved - (prev.internal?.approved || 0),
                cancelled: next.internal.cancelled - (prev.internal?.cancelled || 0),
              },
              draft: {
                draft: next.draft.draft - (prev.draft?.draft || 0),
                submitted: next.draft.submitted - (prev.draft?.submitted || 0),
              },
              pr: {
                submitted: next.pr.submitted - (prev.pr?.submitted || 0),
                approved: next.pr.approved - (prev.pr?.approved || 0),
                under_review: next.pr.under_review - (prev.pr?.under_review || 0),
                rejected: next.pr.rejected - (prev.pr?.rejected || 0),
                cancelled: next.pr.cancelled - (prev.pr?.cancelled || 0),
                converted: next.pr.converted - (prev.pr?.converted || 0),
              },
            };
            setTrends(deltas);
            return next;
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [canInternal, canPurchase, setLoading, setKpis, setTrends]);
};


export default RequisitionsHub;
