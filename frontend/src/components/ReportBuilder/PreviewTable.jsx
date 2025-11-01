import React, { useMemo } from 'react';
import { Card, Empty, Space, Statistic, Table, Typography } from 'antd';
import { AreaChartOutlined, ReloadOutlined } from '@ant-design/icons';

const { Title } = Typography;

const PreviewTable = ({ fields = [], data = [], loading = false, meta = {}, onRefresh }) => {
  const columns = useMemo(() => {
    if (!fields.length && data.length) {
      return Object.keys(data[0] || {}).map((key) => ({
        title: key,
        dataIndex: key,
        key,
      }));
    }
    return fields.map((field) => ({
      title: field.label || field.key,
      dataIndex: field.key,
      key: field.key,
    }));
  }, [fields, data]);

  return (
    <Card
      title={
        <Space>
          <AreaChartOutlined />
          <Title level={5} style={{ margin: 0 }}>
            6. Preview
          </Title>
        </Space>
      }
      extra={
        <Space>
          <Statistic title="Rows" value={meta.total_available || data.length} />
          {meta.limit ? <Statistic title="Preview Limit" value={meta.limit} /> : null}
          <ReloadOutlined style={{ cursor: 'pointer' }} onClick={onRefresh} />
        </Space>
      }
      bordered={false}
    >
      {data.length === 0 ? (
        <Empty description="Run builder preview to see data." />
      ) : (
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey={(_, index) => `preview-${index}`}
          pagination={false}
          size="small"
          scroll={{ x: true }}
        />
      )}
    </Card>
  );
};

export default PreviewTable;
