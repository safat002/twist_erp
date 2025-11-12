import { useAuth } from '../../contexts/AuthContext';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Card, Col, DatePicker, Drawer, Form, Input, Modal, Row, Select, Space, Spin, Table, Tag, Tooltip, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  fetchBudgets,
  fetchBudgetLines,
  fetchModeratorQueue,
  fetchModeratorReviewSummary,
  completeModeratorReview,
  addModeratorRemark,
  batchAddRemarks,
  batchSendBackForReview,
  batchApplyTemplateToCategory,
  fetchRemarkTemplates,
  fetchVarianceAudit,
  fetchLinePricePrediction,
  fetchLineConsumptionForecast,
  updateBudgetLine,
  fetchCostCenters,
  startReviewPeriod,
  closeReviewPeriod,
  getReviewPeriodStatus,
  fetchBudgetAllLines,
  fetchBudget,
} from '../../services/budget';

const PROCUREMENT_OPTIONS = [
  { value: 'stock_item', label: 'Stock Item' },
  { value: 'service_item', label: 'Service / Expense' },
  { value: 'capex_item', label: 'Capex Item' },
];

const ModeratorDashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [budgets, setBudgets] = useState([]);
  const [selectedBudget, setSelectedBudget] = useState(null);
  // Name-only label shown in selector; selection still uses id
  const [selectedBudgetName, setSelectedBudgetName] = useState(null);
  const [lines, setLines] = useState([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [summary, setSummary] = useState(null);

  const [filters, setFilters] = useState({ category: 'ALL', procurement_class: 'ALL', variance: 'ALL', amount: 'ALL' });

  const [remarkModal, setRemarkModal] = useState(false);
  const [remarkText, setRemarkText] = useState('');
  const [remarkTemplate, setRemarkTemplate] = useState(null);

  const [holdModal, setHoldModal] = useState(false);
  const [holdReason, setHoldReason] = useState('');
  const [holdUntil, setHoldUntil] = useState(null);

  const [auditOpen, setAuditOpen] = useState(false);
  const [auditForLine, setAuditForLine] = useState(null);
  const [auditRows, setAuditRows] = useState([]);

  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiForLine, setAiForLine] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiInfo, setAiInfo] = useState(null);
  
  // Track table-applied filters for export
  const [tableFilters, setTableFilters] = useState({});
  const [marking, setMarking] = useState(false);

  // Previous budgets and their line maps for last-2 approved history
  const [prevLinesMap, setPrevLinesMap] = useState({}); // { [budgetId]: { [item_code]: value_limit } }

  // Cost centers lookup
  const [costCenters, setCostCenters] = useState([]);
  // Extra budgets fetched on-demand to ensure status gating works for all CC budgets
  const [extraBudgets, setExtraBudgets] = useState({}); // { [id]: budgetObj }

  // Map cost center id -> display label (e.g., CC-CODE - Name)
  const costCenterMap = useMemo(() => {
    const m = {};
    (costCenters || []).forEach((c) => {
      const name = (c?.name || '').trim();
      const label = name || String(c?.id || '');
      m[String(c.id)] = label;
    });
    return m;
  }, [costCenters]);

  const loadBudgets = useCallback(async () => {
    setLoading(true);
    try {
      // Prefer moderator queue; also include name-approved budgets (exclude only pending_name_approval)
      let queueRows = [];
      try {
        const mq = await fetchModeratorQueue();
        queueRows = Array.isArray(mq?.data) ? mq.data : [];
      } catch (e) {
        console.error('Failed to fetch moderator queue', e);
      }

      let allRows = [];
      try {
        const all = await fetchBudgets({ page_size: 1000 });
        allRows = all?.data?.results || all?.data || [];
      } catch (e) {
        console.error('Failed to fetch all budgets', e);
      }

      const byId = {};
      // Always include queue rows (these should already be post-CC and moderated scope)
      (queueRows || []).forEach((b) => { if (b && b.id != null) byId[String(b.id)] = b; });
      // Include only name-approved budgets from the full list
      (allRows || []).forEach((b) => {
        const ns = String(b?.name_status || '').toUpperCase();
        // Legacy fallback: if name_status absent, exclude only explicit pending_name_approval
        const legacyPending = String(b?.status || '').toLowerCase() === 'pending_name_approval';
        const isNameApproved = ns === 'APPROVED' || (!ns && !legacyPending);
        if (b && b.id != null && isNameApproved) {
          byId[String(b.id)] = byId[String(b.id)] || b;
        }
      });

      // Exclude budgets past review_end_date
      const today = dayjs().startOf('day');
      const combined = Object.values(byId).filter((b) => {
        const re = b?.review_end_date ? dayjs(b.review_end_date) : null;
        if (!re) return true;
        return !today.isAfter(re);
      });
      combined.sort((a, b) => String(b?.period_start || '').localeCompare(String(a?.period_start || '')));
      setBudgets(combined);

      if (!selectedBudget && combined.length) {
        const b0 = combined[0];
        setSelectedBudget(String(b0?.id));
        const nm = (b0?.display_name || b0?.name || b0?.budget_name || '').trim() || ('Budget ' + b0?.id);
        setSelectedBudgetName(nm);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedBudget]);

  const loadTemplates = useCallback(async () => {
    try {
      const { data } = await fetchRemarkTemplates();
      setTemplates(data?.results || data || []);
    } catch (_) {}
  }, []);

  const loadLines = useCallback(async () => {
    if (!selectedBudget) return;
    setLoading(true);
    try {
      // Ask backend for declared + all CC budget lines in one go
      const { data } = await fetchBudgetAllLines(selectedBudget);
      const rows = data?.results || data || [];
      // Build budget id -> CC label map from loaded budgets (including extras)
      const baseMap = {};
      (budgets || []).forEach((b) => { if (b && b.id != null) baseMap[String(b.id)] = b; });
      Object.values(extraBudgets || {}).forEach((b) => { if (b && b.id != null) baseMap[String(b.id)] = b; });
      const budgetMapLabel = {};
      Object.values(baseMap).forEach((b) => {
        const ccLabel = b?.cost_center ? (b?.cost_center_name || costCenterMap[String(b.cost_center)] || String(b.cost_center)) : 'Company-wide';
        budgetMapLabel[String(b.id)] = ccLabel;
      });
      const merged = rows.map((r) => {
        const ccId = r?.metadata?.cost_center_id;
        const ccLabel = ccId ? costCenterMap[String(ccId)] || `Cost Center ${ccId}` : 'Company-wide';
        return { ...r, _budget_id: r.budget, _cc_label: ccLabel };
      });
      const filtered = merged.filter((r) => {
        const ccDecision = String(r.cc_decision || '').toUpperCase();
        if (ccDecision === 'APPROVED') return true;
        // Backward compatibility: fall back to metadata flag if new field missing
        if (!ccDecision && r?.metadata?.approved) return true;
        // For company-wide budgets without CC requirement, allow through
        if (!r?.metadata?.cost_center_id && !r?.cc_decision && !r?.metadata?.approved) {
          return true;
        }
        return false;
      });
      const pendingForModerator = filtered.filter((r) => {
        const finalDecision = String(r.final_decision || '').toUpperCase();
        if (finalDecision === 'APPROVED' || finalDecision === 'REJECTED') return false;
        if (!finalDecision && r?.metadata?.final_approved) return false;
        const modState = String(r.moderator_state || '').toUpperCase();
        if (modState === 'REMARKED') return false;
        if (!modState && (r?.metadata?.reviewed || r?.metadata?.moderator_approved)) return false;
        return true;
      });
      setLines(pendingForModerator);

      // Ensure we have budget details for all budget IDs referenced by lines (for status gating)
      const presentIds = new Set(Object.keys(baseMap));
      const missingIds = Array.from(new Set(merged.map((r) => String(r._budget_id)))).filter((id) => id && !presentIds.has(id));
      if (missingIds.length) {
        try {
          const fetched = await Promise.all(missingIds.map(async (id) => {
            try {
              const res = await fetchBudget(id);
              return res?.data && res.data.id != null ? res.data : null;
            } catch (_) { return null; }
          }));
          const add = {};
          fetched.filter(Boolean).forEach((b) => { add[String(b.id)] = b; });
          if (Object.keys(add).length) setExtraBudgets((prev) => ({ ...prev, ...add }));
        } catch (_) {}
      }
    } catch (e) {
      message.error('Failed to load budget lines');
    } finally {
      setLoading(false);
    }
  }, [selectedBudget, budgets, costCenterMap, extraBudgets]);

  const loadSummary = useCallback(async () => {
    if (!selectedBudget) return;
    try {
      const { data } = await fetchModeratorReviewSummary(selectedBudget);
      setSummary(data);
    } catch (_) {}
  }, [selectedBudget]);

  const onMarkReviewed = useCallback(async () => {
    if (!selectedBudget) return;
    const targets = selectedRowKeys?.length ? selectedRowKeys : (lines || []).map((l) => l.id).filter(Boolean);
    if (!targets.length) {
      message.warning('Select at least one line to mark as reviewed.');
      return;
    }
    setMarking(true);
    try {
      await Promise.all(targets.map((id) => addModeratorRemark(id, { remark_text: 'Approved - Looks Good' })));
      setSelectedRowKeys([]);
      await loadLines();
      await completeModeratorReview(selectedBudget, {});
      await Promise.all([loadBudgets(), loadSummary()]);
      message.success('Marked as reviewed');
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to mark reviewed');
    } finally {
      setMarking(false);
    }
  }, [selectedBudget, selectedRowKeys, lines, loadLines, loadBudgets, loadSummary]);

  const loadCostCenters = useCallback(async () => {
    try {
      const { data } = await fetchCostCenters({ page_size: 1000 });
      setCostCenters(data?.results || data || []);
    } catch (_) {}
  }, []);

  useEffect(() => { loadBudgets(); loadTemplates(); loadCostCenters(); }, [loadBudgets, loadTemplates, loadCostCenters]);
  useEffect(() => { loadLines(); loadSummary(); }, [loadLines, loadSummary]);

  const categories = useMemo(() => ['ALL', ...Array.from(new Set((lines||[]).map(l => l.category).filter(Boolean)))], [lines]);

  // Map budget id -> budget object for quick status checks
  const budgetIndex = useMemo(() => {
    const m = {};
    (budgets || []).forEach((b) => {
      if (b && b.id != null) m[String(b.id)] = b;
    });
    Object.values(extraBudgets || {}).forEach((b) => {
      if (b && b.id != null && !m[String(b.id)]) m[String(b.id)] = b;
    });
    return m;
  }, [budgets, extraBudgets]);

  // Backend now enforces CC-approval gating; frontend only hides reviewed rows

  const filtered = useMemo(() => {
    return (lines || []).filter((l) => {
      // Hide rows only when explicitly marked as reviewed by moderator
      try {
        const meta = l.metadata || {};
        if (meta.reviewed === true) return false;
      } catch (_) {}

      if (l.moderator_remarks) return false;

      if (filters.category !== 'ALL' && l.category !== filters.category) return false;
      if (filters.procurement_class !== 'ALL' && l.procurement_class !== filters.procurement_class) return false;
      if (filters.variance === 'VARIANCE_ONLY') {
        const v = Number(l.value_variance || 0);
        if (v === 0) return false;
      }
      if (filters.variance_pct === 'GT10') {
        if (Math.abs(Number(l.variance_percent || 0)) <= 10) return false;
      }
      if (filters.variance_pct === 'GT20') {
        if (Math.abs(Number(l.variance_percent || 0)) <= 20) return false;
      }
      if (filters.amount === '>5000') {
        if (Number(l.value_limit || 0) <= 5000) return false;
      }
      if (filters.amount === '>10000') {
        if (Number(l.value_limit || 0) <= 10000) return false;
      }
      return true;
    });
  }, [lines, filters]);

  // Resolve selected budget object and cost center display
  const selectedBudgetObj = useMemo(() => {
    try {
      return (budgets || []).find((b) => String(b?.id) === String(selectedBudget)) || null;
    } catch (_) { return null; }
  }, [budgets, selectedBudget]);


  const costCenterLabel = useMemo(() => {
    if (!selectedBudgetObj) return '-';
    const ccId = selectedBudgetObj.cost_center;
    // Preferred: explicit id
    if (ccId) return selectedBudgetObj.cost_center_name || costCenterMap[String(ccId)] || String(ccId);

    // Fallback 1: name provided on object
    const nameOnly = selectedBudgetObj.cost_center_name;
    if (nameOnly) {
      // Try to match against lookup to include code (CC-XXX)
      const match = (costCenters || []).find((c) => String(c?.name || '').trim().toLowerCase() === String(nameOnly).trim().toLowerCase());
      if (match) {
        const codeRaw = (match.code || '').trim();
        const code = codeRaw && !/^CC[-\s]/i.test(codeRaw) ? `CC-${codeRaw}` : codeRaw;
        return code ? `${code} - ${match.name || ''}`.trim() : (match.name || nameOnly);
      }
      // As-is if not found in lookup
      return nameOnly;
    }

    // Fallback 2: derive from approvals if single CC
    const approvals = Array.isArray(selectedBudgetObj.approvals) ? selectedBudgetObj.approvals : [];
    const uniqueNames = Array.from(new Set(approvals.map((a) => (a?.cost_center_name || '').trim()).filter(Boolean)));
    if (uniqueNames.length === 1) {
      const nm = uniqueNames[0];
      const match = (costCenters || []).find((c) => String(c?.name || '').trim().toLowerCase() === nm.toLowerCase());
      if (match) {
        const codeRaw = (match.code || '').trim();
        const code = codeRaw && !/^CC[-\s]/i.test(codeRaw) ? `CC-${codeRaw}` : codeRaw;
        return code ? `${code} - ${match.name || ''}`.trim() : (match.name || nm);
      }
      return nm;
    }

    // Multiple or unknown
    return uniqueNames.length > 1 ? 'Multiple Cost Centers' : 'Company-wide';
  }, [selectedBudgetObj, costCenters, costCenterMap]);

  // Compute last 2 approved budgets for same cost center prior to current period
  const prevBudgets = useMemo(() => {
    if (!selectedBudgetObj) return [];
    const sdate = dayjs(selectedBudgetObj.period_start);
    const APPROVED_STATES = new Set(['APPROVED', 'ACTIVE']);
    const list = (budgets || [])
      .filter((b) => {
        try {
          if (String(b?.id) === String(selectedBudgetObj.id)) return false;
          if (String(b?.cost_center) !== String(selectedBudgetObj.cost_center)) return false;
          if (!APPROVED_STATES.has(b?.status)) return false;
          const ps = dayjs(b?.period_start);
          return ps.isValid() && ps.isBefore(sdate);
        } catch (_) { return false; }
      })
      .sort((a, b) => dayjs(b.period_start).diff(dayjs(a.period_start)))
      .slice(0, 2);
    return list;
  }, [budgets, selectedBudgetObj]);

  // Load previous budgets' lines once identified
  useEffect(() => {
    const run = async () => {
      for (const b of prevBudgets) {
        const bid = String(b.id);
        if (prevLinesMap[bid]) continue;
        try {
          const { data } = await fetchBudgetLines({ budget: bid, page_size: 1000 });
          const rows = data?.results || data || [];
          const m = {};
          rows.forEach((r) => {
            const key = r.budget_item_code || r.budget_item_name;
            if (!key) return;
            m[key] = r.value_limit;
          });
          setPrevLinesMap((prev) => ({ ...prev, [bid]: m }));
        } catch (e) {
          // ignore load error for history
        }
      }
    };
    run();
  }, [prevBudgets, prevLinesMap]);

  const budgetLabel = (b) => {
    if (!b) return '';
    const name = (b.display_name || b.name || '').trim();
    const period = b.period_start && b.period_end ? `${b.period_start} ~ ${b.period_end}` : '';
    return name || period || `Budget ${b.id}`;
  };

  // Export visible rows (respecting top filters + table filters) to CSV (Excel-compatible)
  const exportCsv = () => {
    try {
      // Apply table filters on top of already filtered rows
      let rows = [...filtered];
      const f = tableFilters || {};
      // Item search filter (first value)
      const itemSearch = Array.isArray(f.budget_item_name) && f.budget_item_name[0] ? String(f.budget_item_name[0]).toLowerCase() : '';
      if (itemSearch) {
        rows = rows.filter((r) => (String(r.budget_item_name || '').toLowerCase().includes(itemSearch) || String(r.budget_item_code || '').toLowerCase().includes(itemSearch)));
      }
      // Class filter
      if (Array.isArray(f.procurement_class) && f.procurement_class.length) {
        const set = new Set(f.procurement_class);
        rows = rows.filter((r) => set.has(r.procurement_class));
      }
      // Category filter
      if (Array.isArray(f.category) && f.category.length) {
        const set = new Set(f.category);
        rows = rows.filter((r) => set.has(r.category));
      }
      // Value ranges
      if (Array.isArray(f.value_limit) && f.value_limit.length) {
        const sel = new Set(f.value_limit);
        rows = rows.filter((r) => {
          const v = Number(r.value_limit || 0);
          if (sel.has('LE_5000')) return v <= 5000;
          if (sel.has('GT_10000')) return v > 10000;
          if (sel.has('BT_5_10')) return v > 5000 && v <= 10000;
          return true;
        });
      }
      // Variance filter
      if (Array.isArray(f.variance) && f.variance.length) {
        rows = rows.filter((r) => {
          const v = Number(r.value_variance || 0);
          return f.variance.some((opt) => (opt === 'POS' ? v > 0 : opt === 'ZERO' ? v === 0 : v < 0));
        });
      }

      const pb0 = prevBudgets[0];
      const pb1 = prevBudgets[1];
      const headerParts = [
        'Item Name', 'Item Code', 'Class', 'Category', 'Cost Center', 'Value', 'Variance'
      ];
      if (pb0) headerParts.push(`Prev: ${budgetLabel(pb0)}`);
      if (pb1) headerParts.push(`Prev: ${budgetLabel(pb1)}`);
      const header = headerParts.join(',') + '\n';

      const body = rows.map((r) => {
        const cc = r._cc_label || costCenterLabel;
        const pb0v = pb0 ? (prevLinesMap[String(pb0.id)] || {})[(r.budget_item_code || r.budget_item_name)] : undefined;
        const pb1v = pb1 ? (prevLinesMap[String(pb1.id)] || {})[(r.budget_item_code || r.budget_item_name)] : undefined;
        const parts = [
          `"${String(r.budget_item_name || '').replace(/"/g,'""')}"`,
          `"${String(r.budget_item_code || '').replace(/"/g,'""')}"`,
          r.procurement_class || '',
          `"${String(r.category || '').replace(/"/g,'""')}"`,
          `"${String(cc || '').replace(/"/g,'""')}"`,
          Number(r.value_limit || 0),
          Number(r.value_variance || 0),
        ];
        if (pb0) parts.push(pb0v != null ? Number(pb0v) : '');
        if (pb1) parts.push(pb1v != null ? Number(pb1v) : '');
        return parts.join(',');
      }).join('\n');

      const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'moderator_dashboard_items.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      message.error('Failed to export CSV');
    }
  };

  const exportExcel = () => {
    try {
      // Reuse same filtered logic as CSV
      let rows = [...filtered];
      const f = tableFilters || {};
      const itemSearch = Array.isArray(f.budget_item_name) && f.budget_item_name[0] ? String(f.budget_item_name[0]).toLowerCase() : '';
      if (itemSearch) {
        rows = rows.filter((r) => (String(r.budget_item_name || '').toLowerCase().includes(itemSearch) || String(r.budget_item_code || '').toLowerCase().includes(itemSearch)));
      }
      if (Array.isArray(f.procurement_class) && f.procurement_class.length) {
        const set = new Set(f.procurement_class);
        rows = rows.filter((r) => set.has(r.procurement_class));
      }
      if (Array.isArray(f.category) && f.category.length) {
        const set = new Set(f.category);
        rows = rows.filter((r) => set.has(r.category));
      }
      if (Array.isArray(f.value_limit) && f.value_limit.length) {
        const sel = new Set(f.value_limit);
        rows = rows.filter((r) => {
          const v = Number(r.value_limit || 0);
          if (sel.has('LE_5000')) return v <= 5000;
          if (sel.has('GT_10000')) return v > 10000;
          if (sel.has('BT_5_10')) return v > 5000 && v <= 10000;
          return true;
        });
      }
      if (Array.isArray(f.variance) && f.variance.length) {
        rows = rows.filter((r) => {
          const v = Number(r.value_variance || 0);
          return f.variance.some((opt) => (opt === 'POS' ? v > 0 : opt === 'ZERO' ? v === 0 : v < 0));
        });
      }

      const pb0 = prevBudgets[0];
      const pb1 = prevBudgets[1];
      const headers = ['Cost Center','Item Name','Item Code','Class','Category','Qty','Unit Price','Value','Variance'];
      if (pb0) headers.push(`Prev: ${budgetLabel(pb0)}`);
      if (pb1) headers.push(`Prev: ${budgetLabel(pb1)}`);
      const htmlRows = rows.map((r) => {
        const cc = r._cc_label || costCenterLabel;
        const up = r?.unit_price != null ? r.unit_price : (r?.manual_unit_price != null ? r.manual_unit_price : r?.standard_price);
        const pb0v = pb0 ? (prevLinesMap[String(pb0.id)] || {})[(r.budget_item_code || r.budget_item_name)] : undefined;
        const pb1v = pb1 ? (prevLinesMap[String(pb1.id)] || {})[(r.budget_item_code || r.budget_item_name)] : undefined;
        const cells = [
          cc,
          r.budget_item_name || '',
          r.budget_item_code || '',
          r.procurement_class || '',
          r.category || '',
          Number(r.qty_limit || 0),
          Number(up || 0),
          Number(r.value_limit || 0),
          Number(r.value_variance || 0),
        ];
        if (pb0) cells.push(pb0v != null ? Number(pb0v) : '');
        if (pb1) cells.push(pb1v != null ? Number(pb1v) : '');
        return `<tr>${cells.map((c) => `<td>${String(c).replace(/&/g,'&amp;').replace(/</g,'&lt;')}</td>`).join('')}</tr>`;
      }).join('');

      const table = `<!DOCTYPE html><html><head><meta charset="utf-8" /></head><body><table border="1"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr></thead><tbody>${htmlRows}</tbody></table></body></html>`;
      const blob = new Blob([table], { type: 'application/vnd.ms-excel;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'moderator_dashboard_items.xls';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      message.error('Failed to export Excel');
    }
  };

  const doBatchRemark = async () => {
    const ids = selectedRowKeys;
    if (!ids?.length) return;
    try {
      if (remarkTemplate) {
        await batchAddRemarks({ budget_line_ids: ids, remark_text: remarkText || '', remark_template_id: remarkTemplate });
      } else {
        await batchAddRemarks({ budget_line_ids: ids, remark_text: remarkText || '' });
      }
      message.success('Remarks applied');
      setRemarkModal(false); setRemarkText(''); setRemarkTemplate(null);
      loadLines();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to apply remarks');
    }
  };

  const doBatchSendBack = async () => {
    const ids = selectedRowKeys;
    if (!ids?.length) return;
    try {
      await batchSendBackForReview({ budget_line_ids: ids, reason: remarkText || 'Please review' });
      message.success('Items sent back for review');
      setRemarkModal(false); setRemarkText('');
      loadLines();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to send back items');
    }
  };

  const doBatchHold = async () => {
    const ids = selectedRowKeys;
    if (!ids?.length) return;
    try {
      await Promise.all(ids.map((id) => updateBudgetLine(id, {
        is_held_for_review: true,
        held_reason: holdReason || 'Held for further review',
        held_until_date: holdUntil ? dayjs(holdUntil).toISOString() : null,
      })));
      message.success('Selected items held');
      setHoldModal(false); setHoldReason(''); setHoldUntil(null);
      loadLines();
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Failed to hold items');
    }
  };

  const columns = [
    {
      title: 'Cost Center',
      dataIndex: '_cc_label',
      key: 'cost_center',
      render: (_,_r) => <span>{_r._cc_label || costCenterLabel}</span>,
      filters: Array.from(new Set((lines || []).map((l) => l._cc_label).filter(Boolean))).map((x) => ({ text: x, value: x })),
      onFilter: (v, r) => (r._cc_label || '') === v,
    },
    {
      title: 'Item',
      dataIndex: 'item_name',
      key: 'item_name',
      render: (v, r) => (
        <Space direction="vertical" size={0}>
          <span>{v}</span>
          <span style={{ color: '#999', fontSize: 12 }}>{r.budget_item_code}</span>
        </Space>
      ),
      filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
        <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
          <Input
            placeholder="Search item/code"
            value={selectedKeys[0]}
            onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
            onPressEnter={() => confirm()}
            style={{ marginBottom: 8, display: 'block' }}
          />
          <Space>
            <Button size="small" type="primary" onClick={() => confirm()} icon={<SearchOutlined />}>Search</Button>
            <Button size="small" onClick={() => { clearFilters && clearFilters(); confirm(); }}>Reset</Button>
          </Space>
        </div>
      ),
      filterIcon: (filtered) => (
        <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
      ),
      onFilter: (value, record) => {
        const q = String(value || '').toLowerCase();
        return String(record.budget_item_name || '').toLowerCase().includes(q) || String(record.budget_item_code || '').toLowerCase().includes(q);
      },
    },
    {
      title: 'Class',
      dataIndex: 'procurement_class',
      key: 'procurement_class',
      render: (v) => <Tag>{v}</Tag>,
      filters: PROCUREMENT_OPTIONS.map((o) => ({ text: o.label, value: o.value })),
      onFilter: (v, r) => r.procurement_class === v,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      filters: Array.from(new Set((lines || []).map((l) => l.category).filter(Boolean))).map((c) => ({ text: c, value: c })),
      onFilter: (v, r) => r.category === v,
    },
    {
      title: 'Qty',
      dataIndex: 'qty_limit',
      key: 'qty_limit',
      render: (v) => Number(v || 0).toLocaleString(),
    },
    {
      title: 'Unit Price',
      key: 'unit_price',
      render: (_, r) => {
        const up = r?.unit_price != null ? r.unit_price : (r?.manual_unit_price != null ? r.manual_unit_price : r?.standard_price);
        return Number(up || 0).toLocaleString();
      },
    },
    {
      title: 'Value',
      dataIndex: 'value_limit',
      key: 'value_limit',
      render: (v) => Number(v || 0).toLocaleString(),
      filters: [
        { text: '<= 5k', value: 'LE_5000' },
        { text: '5k - 10k', value: 'BT_5_10' },
        { text: '> 10k', value: 'GT_10000' },
      ],
      onFilter: (v, r) => {
        const val = Number(r.value_limit || 0);
        if (v === 'LE_5000') return val <= 5000;
        if (v === 'GT_10000') return val > 10000;
        if (v === 'BT_5_10') return val > 5000 && val <= 10000;
        return true;
      },
    },
    {
      title: 'Variance',
      key: 'variance',
      filters: [
        { text: 'Negative', value: 'NEG' },
        { text: 'Zero', value: 'ZERO' },
        { text: 'Positive', value: 'POS' },
      ],
      onFilter: (v, r) => {
        const val = Number(r.value_variance || 0);
        if (v === 'NEG') return val < 0;
        if (v === 'ZERO') return val === 0;
        if (v === 'POS') return val > 0;
        return true;
      },
      render: (_, r) => {
        const v = Number(r.value_variance || 0);
        const color = v === 0 ? 'default' : (v > 0 ? 'red' : 'green');
        return <Tag color={color}>{v.toLocaleString()}</Tag>;
      }
    },
    // Previous budgets (last 2) for this cost center
    ...(prevBudgets[0] ? [{
      title: `Prev: ${budgetLabel(prevBudgets[0])}`,
      key: 'prev_budget_0',
      render: (_, r) => {
        const m = prevLinesMap[String(prevBudgets[0].id)] || {};
        const key = r.budget_item_code || r.budget_item_name;
        const v = m[key];
        return v != null ? Number(v).toLocaleString() : '-';
      }
    }] : []),
    ...(prevBudgets[1] ? [{
      title: `Prev: ${budgetLabel(prevBudgets[1])}`,
      key: 'prev_budget_1',
      render: (_, r) => {
        const m = prevLinesMap[String(prevBudgets[1].id)] || {};
        const key = r.budget_item_code || r.budget_item_name;
        const v = m[key];
        return v != null ? Number(v).toLocaleString() : '-';
      }
    }] : []),
    { title: 'Flags', key: 'flags', render: (_, r) => (
      <Space size={4} wrap>
        {r.sent_back_for_review ? <Tag color="orange">Sent Back</Tag> : null}
        {r.is_held_for_review ? <Tag color="gold">Held</Tag> : null}
        {r.moderator_remarks ? <Tooltip title={r.moderator_remarks}><Tag color="blue">Remark</Tag></Tooltip> : null}
      </Space>
    )},
    { title: 'Actions', key: 'actions', render: (_, r) => (
      <Space>
        <Button size="small" onClick={async () => {
          try {
            // Mark approved in metadata and add remark
            const meta = (r.metadata || {});
            await addModeratorRemark(r.id, { remark_text: 'Approved - Looks Good' });
            loadLines();
          } catch (e) { message.error('Failed'); }
        }}>OK</Button>
        <Button size="small" onClick={() => { setAuditForLine(r); setAuditOpen(true); }}>Audit</Button>
        <Button size="small" onClick={async () => {
          setAiForLine(r);
          setAiModalOpen(true);
          setAiLoading(true);
          try {
            const [pred, fc] = await Promise.all([
              fetchLinePricePrediction(r.id).catch(() => ({ data: null })),
              fetchLineConsumptionForecast(r.id).catch(() => ({ data: null })),
            ]);
            setAiInfo({ prediction: pred?.data || null, forecast: fc?.data || null });
          } catch (_) {
            setAiInfo(null);
          } finally {
            setAiLoading(false);
          }
        }}>Insights</Button>
      </Space>
    )},
  ];

  useEffect(() => {
    const run = async () => {
      if (!auditForLine) return;
      try {
        const { data } = await fetchVarianceAudit({ budget_line: auditForLine.id, limit: 100 });
        setAuditRows(data?.results || data || []);
      } catch (_) { setAuditRows([]); }
    };
    run();
  }, [auditForLine]);

  return (
    <>
    <Spin spinning={loading} tip="Loading moderator dashboard">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Row gutter={12} align="middle">
          <Col span={12}>
            <Space>
              <Select
                style={{ minWidth: 320 }}
                placeholder="Select budget"
                value={selectedBudget}
                onChange={(v) => { setSelectedBudget(v); setSelectedRowKeys([]); }}
                options={(budgets||[]).map((b) => {
                  const name = (String(b?.display_name || b?.name || b?.budget_name || '').trim())
                    || `${String(b?.budget_type || '').toUpperCase()} — ${b?.period_start} ~ ${b?.period_end}`
                    || `Budget ${b?.id}`;
                  return ({ value: String(b?.id), label: name });
                })}
              />
              <Select value={filters.category} onChange={(v) => setFilters({ ...filters, category: v })} options={categories.map((c) => ({ value: c, label: c }))} />
              <Select value={filters.procurement_class} onChange={(v) => setFilters({ ...filters, procurement_class: v })} options={[{ value: 'ALL', label: 'All Classes' }, ...PROCUREMENT_OPTIONS]} />
              <Select value={filters.variance} onChange={(v) => setFilters({ ...filters, variance: v })} options={[{ value: 'ALL', label: 'All Items' }, { value: 'VARIANCE_ONLY', label: 'Variance Only' }]} />
              <Select value={filters.variance_pct} onChange={(v) => setFilters({ ...filters, variance_pct: v })} options={[{ value: 'ALL', label: 'Any %' }, { value: 'GT10', label: '> 10%' }, { value: 'GT20', label: '> 20%' }]} />
              <Select value={filters.amount} onChange={(v) => setFilters({ ...filters, amount: v })} options={[{ value: 'ALL', label: 'Any Amount' }, { value: '>5000', label: '> $5k' }, { value: '>10000', label: '> $10k' }]} />
            </Space>
          </Col>
          <Col span={12} style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setRemarkModal(true)}>Add Remark</Button>
              { (user?.is_superuser || (user?.roles || []).some(role => role.name === 'Budget Module Owner')) && (
                <Button onClick={async () => {
                try {
                if (!selectedRowKeys?.length) return;
                // Add remark and mark as reviewed in metadata
                await batchAddRemarks({ budget_line_ids: selectedRowKeys, remark_text: 'Reviewed - Looks Good' });
                const mapById = Object.fromEntries((lines || []).map((x) => [x.id, x]));
                await Promise.all(selectedRowKeys.map((id) => {
                  const base = mapById[id]?.metadata || {};
                  return updateBudgetLine(id, { metadata: { ...base, reviewed: true } });
                }));
                message.success('Reviewed selected');
                setSelectedRowKeys([]);
                loadLines();
                } catch (e) { message.error('Review failed'); }
                }}>Approve Selected</Button>
              )}
              <Button onClick={doBatchSendBack}>Send Back</Button>
              <Button onClick={() => setHoldModal(true)}>Hold</Button>
              <Button onClick={exportExcel}>Export to Excel</Button>
              <Button type="primary" loading={marking} onClick={onMarkReviewed}>Mark Reviewed</Button>
            </Space>
          </Col>
        </Row>

        <Card style={{ marginTop: 8 }}>
          <Space size={16} wrap>
            <Tag color="default">Lines: <strong>{(filtered || []).length}</strong></Tag>
            <Tag color="blue">Total Value: <strong>{((filtered || []).reduce((acc,r)=>acc + Number(r.value_limit || 0), 0)).toLocaleString()}</strong></Tag>
            <Tag color="red">Var% &gt; 10: <strong>{(filtered || []).filter(r => Math.abs(Number(r.variance_percent || 0)) > 10).length}</strong></Tag>
            <Tag color="magenta">Var% &gt; 20: <strong>{(filtered || []).filter(r => Math.abs(Number(r.variance_percent || 0)) > 20).length}</strong></Tag>
            <Tag color="gold">Held: <strong>{(filtered || []).filter(r => r.is_held_for_review).length}</strong></Tag>
            <Tag color="orange">Sent Back: <strong>{(filtered || []).filter(r => r.sent_back_for_review).length}</strong></Tag>
            <Tag color="blue">Remarked: <strong>{(filtered || []).filter(r => (r.moderator_remarks || '').length).length}</strong></Tag>
          </Space>
        </Card>

        <Card>
          <Table
            rowKey="id"
            rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
            dataSource={filtered}
            columns={columns}
            pagination={{ pageSize: 12 }}
            onChange={(_p, filters) => setTableFilters(filters || {})}
          />
        </Card>

        <Modal
          title="Add Remarks (Batch)"
          open={remarkModal}
          onCancel={() => { setRemarkModal(false); setRemarkText(''); setRemarkTemplate(null); }}
          onOk={doBatchRemark}
          okButtonProps={{ disabled: (!remarkText && !remarkTemplate) || !selectedRowKeys?.length }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.TextArea rows={3} placeholder="Remark text" value={remarkText} onChange={(e) => setRemarkText(e.target.value)} />
            <Select
              allowClear
              placeholder="Or choose template"
              value={remarkTemplate}
              onChange={setRemarkTemplate}
              options={(templates||[]).map((t) => ({ value: t.id, label: t.name }))}
            />
          </Space>
            <Space>
              <Button
                onClick={async () => {
                  try {
                    const ids = selectedRowKeys;
                    if (!ids?.length || !remarkTemplate) { message.warning('Select items and a template'); return; }
                    await batchAddRemarks({ budget_line_ids: ids, remark_text: remarkText || '', remark_template_id: remarkTemplate });
                    message.success('Template applied to selected items');
                    setRemarkModal(false); setRemarkText(''); setRemarkTemplate(null);
                    loadLines();
                  } catch (e) { message.error('Failed to apply template'); }
                }}
              >Apply Template to Selected Items</Button>
            </Space>
        </Modal>

        <Modal
          title="Hold Items"
          open={holdModal}
          onCancel={() => { setHoldModal(false); setHoldReason(''); setHoldUntil(null); }}
          onOk={doBatchHold}
          okButtonProps={{ disabled: !selectedRowKeys?.length }}
        >
        </Modal>

        <Drawer
          title={'Variance Audit - ' + (auditForLine?.budget_item_name || '')}
          open={auditOpen}
          width={640}
          onClose={() => { setAuditOpen(false); setAuditForLine(null); setAuditRows([]); }}
        >





          <Table
            size="small"
            dataSource={auditRows}
            columns={[
              { title: 'When', dataIndex: 'created_at' },
              { title: 'Who', dataIndex: 'modified_by_display' },
              { title: 'Type', dataIndex: 'change_type' },
              { title: 'Qty ?', dataIndex: 'qty_variance' },
              { title: 'Price ?', dataIndex: 'price_variance' },
              { title: 'Value ?', dataIndex: 'value_variance' },
              { title: 'Reason', dataIndex: 'modification_reason' },
            ]}
            pagination={{ pageSize: 10 }}
          />
        </Drawer>
      </Space>
    </Spin>
    
    <Modal
      title={aiForLine ? `AI Insights · ${aiForLine.budget_item_name}` : 'AI Insights'}
      onCancel={() => { setAiModalOpen(false); setAiForLine(null); setAiInfo(null); }}
      footer={null}
    >
      <Spin spinning={aiLoading}>
        {aiInfo ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Card size="small" title="Price Prediction">
              {aiInfo.prediction ? (
                <Space direction="vertical" size={2}>
                  <div>Predicted: <strong>{aiInfo.prediction.predicted_price}</strong></div>
                  <div>Confidence: {aiInfo.prediction.confidence || 0}%</div>
                  {aiInfo.prediction.last_po_price ? (<div>Last PO: {aiInfo.prediction.last_po_price}</div>) : null}
                  {aiInfo.prediction.avg_price ? (<div>Avg: {aiInfo.prediction.avg_price}</div>) : null}
                  <div>Method: {aiInfo.prediction.method || '-'}</div>
                </Space>
              ) : 'No prediction available'}
            </Card>
            <Card size="small" title="Consumption Forecast">
              {aiInfo.forecast ? (
                <Space direction="vertical" size={2}>
                  <div>Projected: <strong>{aiInfo.forecast.projected_consumption_value}</strong></div>
                  <div>Confidence: {aiInfo.forecast.confidence || 0}%</div>
                  {aiInfo.forecast.will_exceed_budget ? <Tag color="red">May Exceed</Tag> : <Tag color="green">OK</Tag>}
                  <div>Method: {aiInfo.forecast.method || '-'}</div>
                </Space>
              ) : 'No forecast available'}
            </Card>
          </Space>
        ) : (
          <div>No insights available.</div>
        )}
      </Spin>
    </Modal>
    </>
  );
};

export default ModeratorDashboard;








