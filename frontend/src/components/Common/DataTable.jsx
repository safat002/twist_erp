import React from 'react';
import { Card, Table } from 'antd';

const DataTable = ({
  title,
  columns,
  dataSource,
  loading,
  rowKey = 'id',
  extra,
  pagination,
  size = 'middle',
}) => (
  <Card title={title} extra={extra} bordered={false} style={{ height: '100%' }}>
    <Table
      rowKey={rowKey}
      columns={columns}
      dataSource={dataSource}
      loading={loading}
      pagination={pagination !== undefined ? pagination : { pageSize: 5 }}
      size={size}
    />
  </Card>
);

export default DataTable;
