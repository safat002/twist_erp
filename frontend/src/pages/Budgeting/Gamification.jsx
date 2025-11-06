import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, Col, Empty, Row, Space, Spin, Statistic, Table, Tag, message, Drawer, List } from 'antd';
import { fetchBudgets, fetchLeaderboard, fetchGamificationKpis, fetchBudgetBadges } from '../../services/budget';

const Gamification = () => {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [badgesOpen, setBadgesOpen] = useState(false);
  const [badgesFor, setBadgesFor] = useState(null);
  const [badges, setBadges] = useState([]);
  const [badgesLoading, setBadgesLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [b, l, k] = await Promise.all([
        fetchBudgets(),
        fetchLeaderboard({ limit: 10 }),
        fetchGamificationKpis(),
      ]);
      setRows(b.data?.results || b.data || []);
      setLeaderboard(l.data?.results || l.data || []);
      setKpis(k.data || k || {});
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to load gamification');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const lbColumns = useMemo(() => [
    { title: '#', render: (_, __, idx) => idx + 1, width: 60 },
    { title: 'Budget', dataIndex: 'name' },
    { title: 'Cost Center', dataIndex: 'cost_center' },
    { title: 'Utilization %', dataIndex: 'utilization_percent', render: (v) => <Tag color={Math.abs(Number(v) - 100) <= 5 ? 'green' : 'blue'}>{v}%</Tag> },
    { title: 'Actions', render: (_, r) => <a onClick={async () => {
      setBadgesFor(r);
      setBadgesOpen(true);
      setBadgesLoading(true);
      try {
        const { data } = await fetchBudgetBadges(r.budget_id);
        setBadges(data?.badges || []);
      } catch (_) {
        setBadges([]);
      } finally {
        setBadgesLoading(false);
      }
    }}>View Badges</a> },
  ], []);

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic title="Budgets" value={kpis?.total_budgets || 0} />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic title="Zero-Variance Rate" value={Math.round(kpis?.zero_variance_rate || 0)} suffix="%" />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic title="Early Submission Rate" value={Math.round(kpis?.early_submission_rate || 0)} suffix="%" />
            </Card>
          </Col>
        </Row>

        <Card title="Leaderboard (closest to 100% utilization)">
          {leaderboard.length ? (
            <Table rowKey={(r) => `${r.budget_id}`} dataSource={leaderboard} columns={lbColumns} pagination={false} />
          ) : (
            <Empty description="No leaderboard data" />
          )}
        </Card>

        <Drawer
          title={badgesFor ? `Badges · ${badgesFor.name}` : 'Badges'}
          width={420}
          open={badgesOpen}
          onClose={() => { setBadgesOpen(false); setBadges([]); setBadgesFor(null); }}
        >
          <Spin spinning={badgesLoading}>
            {badges.length ? (
              <List
                dataSource={badges}
                renderItem={(b) => (
                  <List.Item>
                    <List.Item.Meta
                      title={<Space><Tag color="purple">{b.code}</Tag><strong>{b.name}</strong></Space>}
                      description={b.reason}
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="No badges" />
            )}
          </Spin>
        </Drawer>
      </Space>
    </Spin>
  );
};

export default Gamification;

