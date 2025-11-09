import React, { useEffect, useMemo, useState } from 'react';
 param($m) $imp = $m.Groups[1].Value; if ($imp -notmatch 'approveBudgetName') { $imp = $imp.TrimEnd() + ",\n  approveBudgetName,\n  rejectBudgetName,\n  fetchApprovalTaskDetails,\n  approveBudgetLines,\n  requestNameApproval," } ; "import { $imp } from '../../services/budget';" 

const ApprovalQueuePage = () => {
  const [loading, setLoading] = useState(true);
  const [queue, setQueue] = useState([]);
  const [comment, setComment] = useState('');
  const [processingId, setProcessingId] = useState(null);

  // Modal state
  const [modifyOpen, setModifyOpen] = useState(false);
  const [modifyLines, setModifyLines] = useState([]);
  const [modifyBudgetId, setModifyBudgetId] = useState(null);
  const [modifyCostCenterId, setModifyCostCenterId] = useState(null);
  const [lineSelectedKeys, setLineSelectedKeys] = useState([]);
  const [modalApproveAllowed, setModalApproveAllowed] = useState(true);
  const [modalOkText, setModalOkText] = useState('Save Changes & Approve');
  const [currentApprovalTask, setCurrentApprovalTask] = useState(null);

  // Final approval modal state
  const [finalApprovalModalOpen, setFinalApprovalModalOpen] = useState(false);
  const [selectedApprovalTask, setSelectedApprovalTask] = useState(null);
  const [remarkedLines, setRemarkedLines] = useState([]);
  const [selectedLineKeys, setSelectedLineKeys] = useState([]);

  // Modal filters
  const [itemSearch, setItemSearch] = useState('');
  const [lineFilters, setLineFilters] = useState({
    category: 'all',
    procurement_class: 'all',
    changedOnly: false,
    sentBackOnly: false,
    heldOnly: false,
  });

  // Top filters
  const [typeFilter, setTypeFilter] = useState('all'); // 'all' | 'cost_center_owner' | 'budget_module_owner'
  const [statusFilter, setStatusFilter] = useState(['pending']);
  const [textFilter, setTextFilter] = useState('');

  const statusTag = (s) => {
    const map = {
      pending: { color: 'gold', text: 'Pending' },
      approved: { color: 'green', text: 'Approved' },
      rejected: { color: 'red', text: 'Rejected' },
      sent_back: { color: 'orange', text: 'Sent Back' },
    };
    const it = map[s] || { color: 'default', text: s };
    return <Tag color={it.color}>{it.text}</Tag>;
  };

  // Fallback type from budget name if registry value not present
  const typeFromBudgetName = (name) => {
    const s = String(name || '').toLowerCase();
    if (/cap\s*ex|capex|capital/.test(s)) return 'CAPEX';
    if (/op\s*ex|opex|operating|operational/.test(s)) return 'OPEX';
    if (/revenue|sales target/.test(s)) return 'Revenue';
    return '';
  };

  const renderBudgetType = (row) => (row.budget_type ? String(row.budget_type).toUpperCase() : (typeFromBudgetName(row.budget_name) || 'ï¿½'));

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await fetchApprovalQueue();
      const rows = Array.isArray(data) ? data : data?.results || [];
      setQueue(rows);
    } catch (e) {
      message.error('Failed to load approval queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const doAction = async (record, actionFn) => {
  // Handle Name Approval when a registry Draft was surfaced via fallback
  const doNameApproval = async (record, approve = true) => {
    setProcessingId(record.id);
    try {
      const act = approve ? approveBudgetName : rejectBudgetName;
      try {
        await act(record.budget_id, { comments: comment });
      } catch (err) {
        const detail = err?.response?.data?.detail || '';
        if (/not pending name approval/i.test(String(detail))) {
          // Convert to PENDING_NAME_APPROVAL then retry
          await requestNameApproval(record.budget_id);
          await act(record.budget_id, { comments: comment });
        } else {
          throw err;
        }
      }
      setComment('');
      message.success('Action completed');
      load();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed');
    } finally {
      setProcessingId(null);
    }
  };
    setProcessingId(record.id);
    try {
      await actionFn(record.budget_id, { comments: comment });
      setComment('');
      message.success('Action completed');
      load();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed');
    } finally {
      setProcessingId(null);
    }
  };

  const openModifyApprove = async (record) => {
    setCurrentApprovalTask(record);
    try {
      let rows = [];
      if (record.approver_type === 'budget_module_owner') {
        const { data } = await fetchApprovalTaskDetails(record.id);
        rows = data.remarked_lines || [];
      } else {
        const params = { budget: record.cc_budget_id || record.budget_id, page_size: 500 };
        if (record.cost_center_id) params.cost_center = record.cost_center_id;
        const { data } = await fetchBudgetLines(params);
        rows = data?.results || data || [];
        if (record.cost_center_id) {
          const metaFiltered = rows.filter(
            (r) => String(r?.metadata?.cost_center_id || '') === String(record.cost_center_id)
          );
          if (metaFiltered.length > 0) rows = metaFiltered;
        }
      }
      
      setModifyLines(
        rows.map((r) => ({ ...r, _new_qty: r.qty_limit, _new_value: r.value_limit, _reason: '' }))
      );
      setModifyBudgetId(record.cc_budget_id || record.budget_id);
      setModifyCostCenterId(record.cost_center_id || null);
      setModifyOpen(true);
      setLineSelectedKeys([]);
      setItemSearch('');
      setLineFilters({ category: 'all', procurement_class: 'all', changedOnly: false, sentBackOnly: false, heldOnly: false });
      
      const canApprove = (record?.approver_type === 'cost_center_owner') && (!record?.budget_status || record?.budget_status === 'PENDING_CC_APPROVAL');
      setModalApproveAllowed(Boolean(canApprove));
      setModalOkText(Boolean(canApprove) ? 'Save Changes & Approve' : 'Save Changes');
    } catch (e) {
      message.error('Failed to load lines');
    }
  };

  const openFinalApprovalModal = async (record) => {
    try {
      const { data } = await fetchApproval(record.id);
      setSelectedApprovalTask(data);
      setRemarkedLines(data.remarked_lines || []);
      setFinalApprovalModalOpen(true);
      setSelectedLineKeys([]);
    } catch (e) {
      message.error('Failed to load approval details');
    }
  };

  const handleApproveSelectedLines = async () => {
    if (!selectedApprovalTask || !selectedLineKeys.length) return;
    try {
      await approveApprovalLines(selectedApprovalTask.id, { line_ids: selectedLineKeys });
      message.success('Selected lines approved');
      setFinalApprovalModalOpen(false);
      load(); // Refresh the queue
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to approve lines');
    }
  };

  // Apply main filters
  const filtered = useMemo(() => {
    return (queue || []).filter((r) => {
      if (typeFilter !== 'all' && r.approver_type !== typeFilter) return false;
      if (statusFilter && statusFilter.length && !statusFilter.includes(r.status)) return false;
      if (textFilter) {
        const t = textFilter.toLowerCase();
        const a = (r.budget_name || '').toLowerCase();
        const b = (r.cost_center || '').toLowerCase();
        if (!a.includes(t) && !b.includes(t)) return false;
      }
      return true;
    });
  }, [queue, typeFilter, statusFilter, textFilter]);

  const nameData = useMemo(() => filtered.filter((r) => r.approver_type === 'budget_name_approver'), [filtered]);
  const ccData = useMemo(() => filtered.filter((r) => r.approver_type === 'cost_center_owner'), [filtered]);
  const finalData = useMemo(() => filtered.filter((r) => r.approver_type === 'budget_module_owner'), [filtered]);

  // Group cost center approvals by Budget Name (CC-wise under same budget)
  const ccGroups = useMemo(() => {
    const by = new Map();
    (ccData || []).forEach((row) => {
      const key = row.budget_name || 'Untitled Budget';
      if (!by.has(key)) by.set(key, []);
      by.get(key).push(row);
    });
    return Array.from(by.entries()).sort((a, b) => String(a[0]).localeCompare(String(b[0])));
  }, [ccData]);

  const columnsName = [
    { title: 'Budget', dataIndex: 'budget_name' },
    { title: 'Type', dataIndex: 'budget_type', render: (_, r) => renderBudgetType(r) },
    { title: 'Status', dataIndex: 'status', render: (v) => statusTag(v) },
    { title: 'Submitted', dataIndex: 'created_at', render: (v) => (v ? new Date(v).toLocaleString() : '') },
    {
      title: 'Actions',
      render: (_, r) => (
        <Space>
          <Button size="small" type="primary" loading={processingId === r.id} onClick={() => doNameApproval(r, true)}>
            Approve
          </Button>
          <Button size="small" danger loading={processingId === r.id} onClick={() => doNameApproval(r, false)}>
            Reject
          </Button>
        </Space>
      ),
    },
  ];

  const columnsCc = [
    { title: 'Budget', dataIndex: 'budget_name' },
    { title: 'Type', dataIndex: 'budget_type', render: (_, r) => renderBudgetType(r) },
    { title: 'Cost Center', dataIndex: 'cost_center' },
    { title: 'Status', dataIndex: 'status', render: (v) => statusTag(v) },
    { title: 'Submitted', dataIndex: 'created_at', render: (v) => (v ? new Date(v).toLocaleString() : '') },
    {
      title: 'Actions',
      render: (_, r) => (
        <Space>
          <Button size="small" type="primary" loading={processingId === r.id} onClick={() => openModifyApprove(r)}>
            Modify & Approve
          </Button>
          <Button
            size="small"
            danger
            loading={processingId === r.id}
            onClick={async () => {
              setProcessingId(r.id);
              try {
                await rejectCC(r.budget_id, { comments: comment, cost_center: r.cost_center_id });
                setComment('');
                message.success('Sent back');
                load();
              } catch (e) {
                message.error(e?.response?.data?.detail || 'Failed');
              } finally {
                setProcessingId(null);
              }
            }}
          >
            Send Back
          </Button>
        </Space>
      ),
    },
  ];

  const columnsFinal = [
    { title: 'Budget', dataIndex: 'budget_name' },
    { title: 'Type', dataIndex: 'budget_type', render: (_, r) => renderBudgetType(r) },
    { title: 'Cost Center', dataIndex: 'cost_center' },
    { title: 'Status', dataIndex: 'status', render: (v) => statusTag(v) },
    { title: 'Submitted', dataIndex: 'created_at', render: (v) => (v ? new Date(v).toLocaleString() : '') },
    {
      title: 'Actions',
      render: (_, r) => (
        <Space>
          <Button size="small" type="primary" loading={processingId === r.id} onClick={() => openModifyApprove(r)}>
            Modify & Approve
          </Button>
          <Button size="small" danger loading={processingId === r.id} onClick={() => doAction(r, rejectFinal)}>
            Send Back
          </Button>
        </Space>
      ),
    },
  ];

  const modalFilteredLines = useMemo(() => {
    return (modifyLines || []).filter((r) => {
      if (itemSearch && !(r.item_name || '').toLowerCase().includes(itemSearch.toLowerCase())) return false;
      if (lineFilters.category !== 'all' && (r.item_category_name || r.sub_category_name || r.category_name || r.category) !== lineFilters.category) return false;
      if (lineFilters.procurement_class !== 'all' && r.procurement_class !== lineFilters.procurement_class) return false;
      if (lineFilters.changedOnly && !(Number(r._new_qty) !== Number(r.qty_limit) || Number(r._new_value) !== Number(r.value_limit) || (r._reason || '').length)) return false;
      if (lineFilters.sentBackOnly && !r.sent_back_for_review) return false;
      if (lineFilters.heldOnly && !r.is_held_for_review) return false;
      return true;
    });
  }, [modifyLines, itemSearch, lineFilters]);

  return (
    <>
      <Card
        title="Approval Queue"
        extra={(
          <Input.TextArea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Optional comments..."
            rows={1}
            style={{ width: 320 }}
          />
        )}
      >
        <Space style={{ marginBottom: 12 }} wrap>
          <Select
            value={typeFilter}
            onChange={setTypeFilter}
            style={{ width: 220 }}
            options={[
              { value: 'all', label: 'All Types' },
              { value: 'budget_name_approver', label: 'Budget Name Approvals' },
              { value: 'cost_center_owner', label: 'Cost Center Approvals' },
              { value: 'budget_module_owner', label: 'Final Approvals' },
            ]}
          />
          <Select
            mode="multiple"
            allowClear
            placeholder="Status"
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ minWidth: 220 }}
            options={[
              { value: 'pending', label: 'Pending' },
              { value: 'sent_back', label: 'Sent Back' },
              { value: 'approved', label: 'Approved' },
              { value: 'rejected', label: 'Rejected' },
            ]}
          />
          <Input.Search
            placeholder="Search budget or cost center"
            allowClear
            onChange={(e) => setTextFilter(e.target.value)}
            style={{ width: 260 }}
          />
          <Button onClick={load}>Refresh</Button>
        </Space>

        <Tabs
          items={[
            ...(typeFilter === 'all' || typeFilter === 'budget_name_approver'
              ? [{
                  key: 'name',
                  label: `Budget Name Approvals (${nameData.length})`,
                  children: (
                    <Table rowKey="id" loading={loading} dataSource={nameData} columns={columnsName} pagination={{ pageSize: 10 }} />
                  ),
                }]
              : []),
            ...(typeFilter === 'all' || typeFilter === 'cost_center_owner'
              ? [{
                  key: 'cc',
                  label: `Cost Center Approvals (${ccData.length})`,
                  children: (
                    ccGroups.length ? (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {ccGroups.map(([budgetName, rows]) => (
                          <Card key={budgetName} size="small" title={budgetName}>
                            <Table rowKey="id" loading={loading} dataSource={rows} columns={columnsCc} pagination={false} />
                          </Card>
                        ))}
                      </Space>
                    ) : (
                      <Empty description="No pending CC approvals" />
                    )
                  ),
                }]
              : []),
            ...(typeFilter === 'all' || typeFilter === 'budget_module_owner'
              ? [{
                  key: 'final',
                  label: `Final Approvals (${finalData.length})`,
                  children: (
                    <Table rowKey="id" loading={loading} dataSource={finalData} columns={columnsFinal} pagination={{ pageSize: 10 }} />
                  ),
                }]
              : []),
          ]}
        />
      </Card>

      <Modal
        title="Modify Lines & Approve"
        open={modifyOpen}
        width={1280}
        okText={modalOkText}
        onCancel={() => {
          setModifyOpen(false);
          setModifyLines([]);
          setModifyBudgetId(null);
        }}
        onOk={async () => {
          try {
            const diff = modifyLines.filter(
              (r) => r._new_qty !== r.qty_limit || r._new_value !== r.value_limit || (r._reason || '').length
            );
            if (diff.length > 0) {
              await Promise.all(
                diff.map((r) =>
                  updateBudgetLine(r.id, {
                    qty_limit: r._new_qty,
                    value_limit: r._new_value,
                    modification_reason: r._reason,
                  })
                )
              );
              message.success('Changes saved');
            }

            if (currentApprovalTask.approver_type === 'cost_center_owner') {
              const canApprove = Boolean(!currentApprovalTask.budget_status || currentApprovalTask.budget_status === 'PENDING_CC_APPROVAL');
              if (canApprove) {
                // Refresh current lines, keeping CC scope if any
                let refreshed = [];
                try {
                  const params = { budget: modifyBudgetId, page_size: 500 };
                  if (modifyCostCenterId) params.cost_center = modifyCostCenterId;
                  const { data } = await fetchBudgetLines(params);
                  refreshed = data?.results || data || [];
                  if (modifyCostCenterId) {
                    const metaFiltered = refreshed.filter((r) => String(r?.metadata?.cost_center_id || '') === String(modifyCostCenterId));
                    if (metaFiltered.length > 0) refreshed = metaFiltered;
                  }
                } catch (_) {
                  refreshed = [];
                }
                // Only finalize CC approval if all items are approved or sent back
                const allCleared = (refreshed || []).every((r) => (r?.metadata?.approved === true) || r?.sent_back_for_review === true);
                if (allCleared) {
                  await approveCC(modifyBudgetId, { comments: comment, cost_center: modifyCostCenterId || currentApprovalTask.cost_center_id });
                  message.success('CC approval completed');
                } else {
                  message.info('Some items are not approved yet. Saved changes only.');
                }
              }
            }
            
            setModifyOpen(false);
            setModifyLines([]);
            setModifyBudgetId(null);
            setComment('');
            load();
          } catch (e) {
            message.error(e?.response?.data?.detail || 'Failed to process approval');
          }
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            <Input.Search
              placeholder="Search item"
              allowClear
              style={{ width: 240 }}
              value={itemSearch}
              onChange={(e) => setItemSearch(e.target.value)}
            />
            <Select
              style={{ width: 220 }}
              value={lineFilters.category}
              onChange={(v) => setLineFilters((f) => ({ ...f, category: v }))}
              options={[
                { value: 'all', label: 'All Item Categories' },
                ...Array.from(
                  new Set(
                    (modifyLines || [])
                      .map((x) => x.item_category_name || x.sub_category_name || x.category_name || x.category)
                      .filter(Boolean)
                  )
                ).map((c) => ({ value: c, label: c })),
              ]}
            />
            <Select
              style={{ width: 220 }}
              value={lineFilters.procurement_class}
              onChange={(v) => setLineFilters((f) => ({ ...f, procurement_class: v }))}
              options={[
                { value: 'all', label: 'All Procurement Classes' },
                ...Array.from(new Set((modifyLines || []).map((x) => x.procurement_class).filter(Boolean))).map((p) => ({
                  value: p,
                  label: (p || '').replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase()),
                })),
              ]}
            />
            <Checkbox
              checked={lineFilters.changedOnly}
              onChange={(e) => setLineFilters((f) => ({ ...f, changedOnly: e.target.checked }))}
            >
              Changed Only
            </Checkbox>
            <Checkbox
              checked={lineFilters.sentBackOnly}
              onChange={(e) => setLineFilters((f) => ({ ...f, sentBackOnly: e.target.checked }))}
            >
              Sent Back Only
            </Checkbox>
            <Checkbox
              checked={lineFilters.heldOnly}
              onChange={(e) => setLineFilters((f) => ({ ...f, heldOnly: e.target.checked }))}
            >
              Held Only
            </Checkbox>
          </Space>

          <Space>
            <Button
              disabled={!lineSelectedKeys.length}
              type="primary"
              onClick={async () => {
                try {
                  if (currentApprovalTask.approver_type === 'budget_module_owner') {
                    await approveBudgetLines(currentApprovalTask.id, lineSelectedKeys);
                    message.success('Selected lines approved');
                  } else {
                    const mapById = Object.fromEntries((modifyLines || []).map((r) => [r.id, r]));
                    await Promise.all(
                      lineSelectedKeys.map((id) => {
                        const r = mapById[id];
                        const metadata = { ...(r?.metadata || {}), approved: true, rejected: false };
                        return updateBudgetLine(id, { metadata });
                      })
                    );
                    message.success('Selected lines marked as approved');
                  }
                  // Reload lines and keep CC scope
                  {
                    const params = { budget: modifyBudgetId, page_size: 500 };
                    if (modifyCostCenterId) params.cost_center = modifyCostCenterId;
                    const { data } = await fetchBudgetLines(params);
                    let rows = data?.results || data || [];
                    if (modifyCostCenterId) {
                      const metaFiltered = rows.filter((r) => String(r?.metadata?.cost_center_id || '') === String(modifyCostCenterId));
                      if (metaFiltered.length > 0) rows = metaFiltered;
                    }
                    setModifyLines(rows.map((r) => ({ ...r, _new_qty: r.qty_limit, _new_value: r.value_limit, _reason: '' })));
                  }
                } catch (e) {
                  message.error(e?.response?.data?.detail || 'Failed to approve');
                }
              }}
            >
              Approve Selected
            </Button>
            <Button
              danger
              disabled={!lineSelectedKeys.length}
              onClick={() => {
                let reason = '';
                Modal.confirm({
                  title: 'Reject Selected (Send Back for Review)',
                  content: (
                    <Input.TextArea
                      rows={3}
                      placeholder="Reason (optional)"
                      onChange={(e) => {
                        reason = e.target.value;
                      }}
                    />
                  ),
                  okText: 'Send Back',
                  onOk: async () => {
                    try {
                        await Promise.all(lineSelectedKeys.map((id) => sendBackLineForReview(id, reason)));
                        message.success('Selected lines rejected and sent back for review');
                        // Reload lines and keep CC scope
                        {
                          const params = { budget: modifyBudgetId, page_size: 500 };
                          if (modifyCostCenterId) params.cost_center = modifyCostCenterId;
                          const { data } = await fetchBudgetLines(params);
                          let rows = data?.results || data || [];
                          if (modifyCostCenterId) {
                            const metaFiltered = rows.filter((r) => String(r?.metadata?.cost_center_id || '') === String(modifyCostCenterId));
                            if (metaFiltered.length > 0) rows = metaFiltered;
                          }
                          setModifyLines(rows.map((r) => ({ ...r, _new_qty: r.qty_limit, _new_value: r.value_limit, _reason: '' })));
                          setLineSelectedKeys([]);
                        }
                      setLineSelectedKeys([]);
                    } catch (e) {
                      message.error(e?.response?.data?.detail || 'Failed to send back');
                    }
                  },
                });
              }}
            >
              Send Back Selected
            </Button>
            <Button onClick={() => setLineSelectedKeys([])} disabled={!lineSelectedKeys.length}>
              Clear Selection
            </Button>
          </Space>

          <Divider style={{ margin: '8px 0' }} />

          <Table
            rowKey="id"
            dataSource={modalFilteredLines}
            pagination={{ pageSize: 8 }}
            rowSelection={{
              selectedRowKeys: lineSelectedKeys,
              onChange: setLineSelectedKeys,
              preserveSelectedRowKeys: true,
            }}
            columns={[
              {
                title: 'Item',
                dataIndex: 'item_name',
                filteredValue: itemSearch ? [itemSearch] : null,
                onFilter: (v, r) => (r.item_name || '').toLowerCase().includes(String(v).toLowerCase()),
              },
              {
                title: 'Item Category',
                dataIndex: 'item_category_name',
                filters: Array.from(
                  new Set(
                    (modifyLines || [])
                      .map((x) => x.item_category_name || x.sub_category_name || x.category_name || x.category)
                      .filter(Boolean)
                  )
                ).map((c) => ({ text: c, value: c })),
                onFilter: (v, r) => (r.item_category_name || r.sub_category_name || r.category_name || r.category) === v,
                render: (_, r) => r.item_category_name || r.sub_category_name || r.category_name || r.category || '',
              },
              {
                title: 'Sub-Category',
                dataIndex: 'sub_category_name',
                filters: Array.from(new Set((modifyLines || []).map((x) => x.sub_category_name).filter(Boolean))).map((c) => ({ text: c, value: c })),
                onFilter: (v, r) => r.sub_category_name === v,
                render: (v) => v || '',
              },
              {
                title: 'Procurement Class',
                dataIndex: 'procurement_class',
                filters: Array.from(new Set((modifyLines || []).map((x) => x.procurement_class).filter(Boolean))).map((p) => ({ text: p, value: p })),
                onFilter: (v, r) => r.procurement_class === v,
                render: (v) => (v || '').replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase()),
              },
              {
                title: 'Qty',
                render: (_, r) => (
                  <Input
                    type="number"
                    value={r._new_qty}
                    onChange={(e) =>
                      setModifyLines((prev) => prev.map((x) => (x.id === r.id ? { ...x, _new_qty: Number(e.target.value) } : x)))
                    }
                    style={{ width: 100 }}
                  />
                ),
              },
              {
                title: 'Value',
                render: (_, r) => (
                  <Input
                    type="number"
                    value={r._new_value}
                    onChange={(e) =>
                      setModifyLines((prev) => prev.map((x) => (x.id === r.id ? { ...x, _new_value: Number(e.target.value) } : x)))
                    }
                    style={{ width: 140 }}
                  />
                ),
              },
              {
                title: 'Status',
                filters: [
                  { text: 'Changed', value: 'changed' },
                  { text: 'Approved', value: 'approved' },
                  { text: 'Rejected', value: 'rejected' },
                  { text: 'Sent Back', value: 'sent_back' },
                  { text: 'Held', value: 'held' },
                ],
                onFilter: (v, r) => {
                  if (v === 'changed') return (
                    Number(r._new_qty) !== Number(r.qty_limit) ||
                    Number(r._new_value) !== Number(r.value_limit) ||
                    (r._reason || '').length
                  );
                  if (v === 'approved') return r.status === 'approved';
                  if (v === 'rejected') return r.status === 'rejected';
                  if (v === 'sent_back') return !!r.sent_back_for_review;
                  if (v === 'held') return !!r.is_held_for_review;
                  return true;
                },
                render: (_, r) => (
                  <Space size={4}>
                    {Number(r._new_qty) !== Number(r.qty_limit) || Number(r._new_value) !== Number(r.value_limit) || (r._reason || '').length ? (
                      <Tag color="blue">Changed</Tag>
                    ) : null}
                    {r.status === 'approved' ? <Tag color="green">Approved</Tag> : null}
                    {r.status === 'rejected' ? <Tag color="red">Rejected</Tag> : null}
                    {r.sent_back_for_review ? <Tag color="orange">Sent Back</Tag> : null}
                    {r.is_held_for_review ? <Tag color="magenta">Held</Tag> : null}
                  </Space>
                ),
              },
              {
                title: 'Reason',
                render: (_, r) => (
                  <Input
                    value={r._reason}
                    onChange={(e) =>
                      setModifyLines((prev) => prev.map((x) => (x.id === r.id ? { ...x, _reason: e.target.value } : x)))
                    }
                  />
                ),
              },
            ]}
          />
        </Space>
      </Modal>

      <Modal
        title="Final Approval - Remarked Items"
        open={finalApprovalModalOpen}
        width={1280}
        onCancel={() => setFinalApprovalModalOpen(false)}
        onOk={handleApproveSelectedLines}
        okText="Approve Selected Lines"
      >
        <Table
          rowKey="id"
          dataSource={remarkedLines}
          rowSelection={{
            selectedRowKeys: selectedLineKeys,
            onChange: setSelectedLineKeys,
          }}
          columns={[
            { title: 'Item', dataIndex: 'item_name' },
            { title: 'Moderator Remarks', dataIndex: 'moderator_remarks' },
            { title: 'Value', dataIndex: 'value_limit' },
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Modal>
    </>
  );
};

export default ApprovalQueuePage;











