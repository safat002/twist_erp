import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Timeline,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  SendOutlined,
  StopOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useCompany } from '../../../contexts/CompanyContext';
import api from '../../../services/api';
import {
  approveMaterialIssue,
  cancelMaterialIssue,
  createMaterialIssue,
  getAvailableBatches,
  getAvailableSerials,
  getMaterialIssue,
  getMaterialIssues,
  issueMaterial,
  submitMaterialIssue,
  updateMaterialIssue,
  getInternalRequisitions,
  getInternalRequisition,
} from '../../../services/materialIssue';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

const STATUS_OPTIONS = [
  { label: 'All', value: 'ALL' },
  { label: 'Draft', value: 'DRAFT' },
  { label: 'Submitted', value: 'SUBMITTED' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Issued', value: 'ISSUED' },
  { label: 'Closed', value: 'CLOSED' },
  { label: 'Cancelled', value: 'CANCELLED' },
];

const ISSUE_TYPE_OPTIONS = [
  { label: 'Production', value: 'PRODUCTION' },
  { label: 'Department', value: 'DEPARTMENT' },
  { label: 'Sales Order', value: 'SALES_ORDER' },
  { label: 'Project', value: 'PROJECT' },
  { label: 'Cost Center', value: 'COST_CENTER' },
  { label: 'Sample', value: 'SAMPLE' },
  { label: 'Other', value: 'OTHER' },
];

const STATUS_TAGS = {
  DRAFT: { color: 'default', text: 'Draft' },
  SUBMITTED: { color: 'blue', text: 'Submitted' },
  APPROVED: { color: 'gold', text: 'Approved' },
  ISSUED: { color: 'green', text: 'Issued' },
  PARTIALLY_RETURNED: { color: 'purple', text: 'Partially Returned' },
  CLOSED: { color: 'cyan', text: 'Closed' },
  CANCELLED: { color: 'red', text: 'Cancelled' },
};

const asArray = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.results)) return payload.results;
  if (payload.data) {
    if (Array.isArray(payload.data)) return payload.data;
    if (Array.isArray(payload.data?.results)) return payload.data.results;
  }
  return [];
};

const getPrimitiveId = (value) => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'object') {
    return value.id ?? value.value ?? value.pk ?? null;
  }
  return value;
};

const formatBatchLabel = (batch) => {
  if (!batch) return '';
  const code = batch.batch_no || batch.batch_code || batch.lot || batch.name || batch.id;
  const exp = batch.expiry_date ? dayjs(batch.expiry_date).format('MMM D, YYYY') : null;
  const qty = Number(batch.available_quantity ?? batch.available_qty ?? batch.balance_qty ?? 0);
  const uom = batch.uom || batch.stock_uom || '';
  return `${code}${exp ? ` - Exp ${exp}` : ''}${qty ? ` - ${qty} ${uom}` : ''}`;
};

const formatSerialValue = (serial) => {
  if (!serial) return '';
  if (typeof serial === 'string') return serial;
  return serial.serial || serial.serial_no || serial.code || serial.id || '';
};
const MaterialIssueManagement = () => {
  const { currentCompany } = useCompany();
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailDrawer, setDetailDrawer] = useState({ visible: false, record: null, loading: false });
  const [editingIssue, setEditingIssue] = useState(null);
  const [saveLoading, setSaveLoading] = useState(false);
  const [referenceLoading, setReferenceLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [warehouses, setWarehouses] = useState([]);
  const [budgetItems, setBudgetItems] = useState([]);
  const [costCenters, setCostCenters] = useState([]);
  const [projects, setProjects] = useState([]);
  const [batchCache, setBatchCache] = useState({});
  const [serialCache, setSerialCache] = useState({});
  const [internalRequisitions, setInternalRequisitions] = useState([]);
  const [requisitionListLoading, setRequisitionListLoading] = useState(false);
  const [requisitionDetails, setRequisitionDetails] = useState({});
  const [requisitionSyncing, setRequisitionSyncing] = useState(false);
  const [cancelModal, setCancelModal] = useState({ visible: false, record: null, loading: false });
  const [form] = Form.useForm();
  const [cancelForm] = Form.useForm();

  const lines = Form.useWatch('lines', form) || [];

  const budgetItemMap = useMemo(
    () =>
      (budgetItems || []).reduce((acc, item) => {
        acc[item.id] = item;
        return acc;
      }, {}),
    [budgetItems]
  );

  const requisitionOptions = useMemo(
    () =>
      (internalRequisitions || []).map((req) => ({
        value: req.id,
        label: req.requisition_number || `IR-${req.id}`,
        description: `${req.lines?.length || 0} lines${req.purpose ? ` • ${req.purpose.substring(0, 40)}${req.purpose.length > 40 ? '…' : ''}` : ''}`,
      })),
    [internalRequisitions]
  );

  const costCenterOptions = useMemo(
    () =>
      (costCenters || []).map((cc) => ({
        value: cc.id,
        label: `${cc.code || ''} ${cc.name || ''}`.trim(),
      })),
    [costCenters]
  );

  const projectOptions = useMemo(
    () =>
      (projects || []).map((project) => ({
        value: project.id,
        label: project.name || project.code || `Project ${project.id}`,
      })),
    [projects]
  );

  const budgetItemOptions = useMemo(
    () =>
      (budgetItems || []).map((item) => {
        const code = item.code || '';
        const name = item.name || '';
        const baseLabel = `${code} - ${name}`.trim() || code || name || `Item ${item.id}`;
        const status = (item.status || '').toUpperCase();
        return {
          value: item.id,
          label: status && status !== 'ACTIVE' ? `${baseLabel} (${status})` : baseLabel,
          disabled: Boolean(status && status !== 'ACTIVE'),
        };
      }),
    [budgetItems]
  );

  const getBudgetItemDefaults = useCallback(
    (budgetItemId) => {
      if (!budgetItemId) return {};
      const record = budgetItemMap[String(budgetItemId)];
      if (!record) return {};

      const normalizeUomId = (value) => {
        if (!value && value !== 0) return null;
        if (typeof value === 'string' || typeof value === 'number') return value;
        if (typeof value === 'object') {
          return value.id ?? value.value ?? null;
        }
        return null;
      };

      const uomId = normalizeUomId(record.stock_uom) ?? normalizeUomId(record.uom);
      const uomLabel =
        record.stock_uom_name ||
        record.uom_name ||
        record.stock_uom?.name ||
        record.uom?.name ||
        '';
      const valuationRate =
        Number(
          record.valuation_rate ??
            record.standard_cost ??
            record.cost_price ??
            0
        ) || 0;

      return {
        record,
        uomId,
        uomLabel,
        valuationRate,
      };
    },
    [budgetItemMap]
  );

  const warehouseOptions = useMemo(
    () =>
      (warehouses || []).map((wh) => ({
        value: wh.id,
        label: `${wh.code || ''} ${wh.name || ''}`.trim(),
      })),
    [warehouses]
  );
  const getLineUnitCost = useCallback(
    (line) => {
      if (!line) return 0;
      if (line.unit_cost) return Number(line.unit_cost) || 0;
      const defaults = getBudgetItemDefaults(line.budget_item);
      return Number(line.valuation_rate ?? defaults.valuationRate ?? 0) || 0;
    },
    [getBudgetItemDefaults]
  );

  const getLineUomLabel = useCallback(
    (line) => {
      if (!line) return '';
      if (line.uom_label) return line.uom_label;
      const defaults = getBudgetItemDefaults(line.budget_item);
      return defaults.uomLabel || '';
    },
    [getBudgetItemDefaults]
  );

  const getLineCost = useCallback(
    (line) => {
      const qty = Number(line?.quantity_requested ?? line?.quantity ?? 0) || 0;
      return qty * getLineUnitCost(line);
    },
    [getLineUnitCost]
  );

  const totalEstimatedCost = useMemo(
    () => (lines || []).reduce((sum, line) => sum + getLineCost(line), 0),
    [lines, getLineCost]
  );

  const normalizeRequisitionLine = useCallback(
    (line) => {
      if (!line) return null;
      const budgetItemId =
        line.budget_item ||
        line.budget_item_id ||
        null;
      if (!budgetItemId) return null;

      const defaults = getBudgetItemDefaults(budgetItemId);
      const quantity =
        Number(
          line.quantity ??
            line.qty ??
            line.quantity_requested ??
            line.requested_quantity ??
            0
        ) || 0;
      if (quantity <= 0) return null;

      return {
        budget_item: budgetItemId,
        quantity_requested: quantity,
        quantity_issued: quantity,
        uom: defaults.uomId,
        uom_label: defaults.uomLabel,
        batch_lot: null,
        serial_numbers: [],
        cost_center: null,
        project: null,
        notes: line.notes || '',
        unit_cost: defaults.valuationRate,
        valuation_rate: defaults.valuationRate,
      };
    },
    [getBudgetItemDefaults]
  );

  const applyRequisitionsToForm = useCallback(
    async (requisitionIds) => {
      if (!Array.isArray(requisitionIds) || !requisitionIds.length) return;

      const missingIds = requisitionIds.filter((id) => !requisitionDetails[id]);
      let fetched = {};
      if (missingIds.length) {
        const responses = await Promise.allSettled(
          missingIds.map((id) => getInternalRequisition(id))
        );
        responses.forEach((res, idx) => {
          if (res.status === 'fulfilled') {
            fetched[missingIds[idx]] = res.value.data;
          }
        });
        if (Object.keys(fetched).length) {
          setRequisitionDetails((prev) => ({ ...prev, ...fetched }));
        }
      }

      const detailMap = { ...requisitionDetails, ...fetched };
      const selectedDetails = requisitionIds
        .map((id) => detailMap[id])
        .filter(Boolean);
      if (!selectedDetails.length) {
        return;
      }

      const requisitionLines = selectedDetails
        .flatMap((req) => (Array.isArray(req.lines) ? req.lines : []))
        .map((line) => normalizeRequisitionLine(line))
        .filter(Boolean);

      if (requisitionLines.length) {
        form.setFieldsValue({ lines: requisitionLines });
      }

      const primary = selectedDetails[0];
      const patch = {};
      if (primary?.warehouse && !form.getFieldValue('warehouse')) {
        patch.warehouse = primary.warehouse;
      }
      if (primary?.purpose && !form.getFieldValue('purpose')) {
        patch.purpose = primary.purpose;
      }
      if (Object.keys(patch).length) {
        form.setFieldsValue(patch);
      }
    },
    [form, normalizeRequisitionLine, requisitionDetails]
  );

  const handleLinkedRequisitionChange = useCallback(
    async (ids) => {
      if (!ids?.length) {
        form.setFieldsValue({ linked_requisitions: [] });
        return;
      }
      setRequisitionSyncing(true);
      try {
        await applyRequisitionsToForm(ids);
      } catch (error) {
        message.error('Unable to pull requisition lines.');
      } finally {
        setRequisitionSyncing(false);
      }
    },
    [applyRequisitionsToForm, form]
  );

  const loadReferenceData = useCallback(async () => {
    if (!currentCompany?.id) return;
    setReferenceLoading(true);
    try {
      const responses = await Promise.allSettled([
        api.get('/api/v1/inventory/warehouses/', { params: { limit: 500 } }),
        api.get('/api/v1/budgets/item-codes/', {
          params: { limit: 500, status: 'ACTIVE', item_type: 'GOODS' },
        }),
        api.get('/api/v1/budgets/cost-centers/', { params: { limit: 500 } }),
        api.get('/api/v1/projects/', { params: { limit: 500 } }),
      ]);
      const [warehouseRes, budgetRes, costCenterRes, projectRes] = responses;
      if (warehouseRes.status === 'fulfilled') {
        setWarehouses(asArray(warehouseRes.value.data));
      }
      if (budgetRes.status === 'fulfilled') {
        setBudgetItems(asArray(budgetRes.value.data));
      }
      if (costCenterRes.status === 'fulfilled') {
        setCostCenters(asArray(costCenterRes.value.data));
      }
      if (projectRes.status === 'fulfilled') {
        setProjects(asArray(projectRes.value.data));
      }
    } catch (error) {
      message.error('Unable to load reference data for material issues.');
    } finally {
      setReferenceLoading(false);
    }
  }, [currentCompany?.id]);

  const loadInternalRequisitions = useCallback(async () => {
    if (!currentCompany?.id) return;
    setRequisitionListLoading(true);
    try {
      const { data } = await getInternalRequisitions({ status: 'APPROVED' });
      setInternalRequisitions(asArray(data));
    } catch (error) {
      message.warning('Unable to load internal requisitions.');
      setInternalRequisitions([]);
    } finally {
      setRequisitionListLoading(false);
    }
  }, [currentCompany?.id]);

  const loadIssues = useCallback(async () => {
    if (!currentCompany?.id) {
      setIssues([]);
      return;
    }
    try {
      setLoading(true);
      const params = {};
      if (statusFilter && statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      const { data } = await getMaterialIssues(params);
      setIssues(asArray(data));
    } catch (error) {
      message.error(error?.response?.data?.detail || 'Unable to load material issues.');
    } finally {
      setLoading(false);
    }
  }, [currentCompany?.id, statusFilter]);

  useEffect(() => {
    loadReferenceData();
  }, [loadReferenceData]);

  useEffect(() => {
    if (drawerOpen) {
      loadInternalRequisitions();
    }
  }, [drawerOpen, loadInternalRequisitions]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  const resetLineCaches = () => {
    setBatchCache({});
    setSerialCache({});
  };

  const openCreateDrawer = () => {
    setEditingIssue(null);
    resetLineCaches();
    form.resetFields();
    form.setFieldsValue({
      issue_type: 'DEPARTMENT',
      issue_date: dayjs(),
      linked_requisitions: [],
      lines: [{ quantity_requested: 1 }],
    });
    setDrawerOpen(true);
  };

  const openEditDrawer = (record) => {
    setEditingIssue(record);
    resetLineCaches();
    form.resetFields();
        form.setFieldsValue({
          issue_type: record.issue_type,
          warehouse: getPrimitiveId(record.warehouse),
          cost_center: getPrimitiveId(record.cost_center),
          project: getPrimitiveId(record.project),
          department: record.department,
          issue_date: record.issue_date ? dayjs(record.issue_date) : dayjs(),
          purpose: record.purpose,
          notes: record.notes,
          linked_requisitions: record.requisition ? [getPrimitiveId(record.requisition)] : [],
          lines: (record.lines || []).map((line) => ({
            id: line.id,
            budget_item: getPrimitiveId(line.budget_item),
            uom: getPrimitiveId(line.uom),
            uom_label: line.uom_code || line.uom_label || '',
            quantity_requested:
              Number(line.quantity_requested ?? line.quantity ?? line.quantity_issued ?? 0) || 1,
            quantity_issued: Number(line.quantity_issued ?? line.quantity_requested ?? 0) || 1,
            batch_lot: typeof line.batch_lot === 'object' ? line.batch_lot.batch_no : line.batch_lot,
            serial_numbers: Array.isArray(line.serial_numbers)
              ? line.serial_numbers.map((serial) => formatSerialValue(serial))
              : [],
            cost_center: getPrimitiveId(line.cost_center),
            project: getPrimitiveId(line.project),
            notes: line.notes,
            unit_cost: Number(line.unit_cost ?? line.valuation_rate ?? 0) || undefined,
            valuation_rate: Number(line.valuation_rate ?? 0) || undefined,
          })),
        });
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setEditingIssue(null);
    form.resetFields();
  };

  const updateLineField = (index, updates) => {
    const currentLines = [...(form.getFieldValue('lines') || [])];
    currentLines[index] = { ...(currentLines[index] || {}), ...updates };
    form.setFieldsValue({ lines: currentLines });
  };

  const handleBudgetItemSelect = useCallback(
    (budgetItemId, index) => {
      if (!budgetItemId) {
        updateLineField(index, {
          budget_item: null,
          uom: null,
          uom_label: '',
          unit_cost: null,
          valuation_rate: null,
        });
        return;
      }
      const defaults = getBudgetItemDefaults(budgetItemId);
      updateLineField(index, {
        budget_item: budgetItemId,
        uom: defaults.uomId,
        uom_label: defaults.uomLabel,
        unit_cost: defaults.valuationRate,
        valuation_rate: defaults.valuationRate,
      });
      if (!defaults.uomId) {
        message.warning(
          'Selected item is missing a stock UOM. Update the item master to issue stock.'
        );
      }
    },
    [getBudgetItemDefaults, updateLineField]
  );

  const refreshBatches = async (warehouseId, budgetItemId) => {
    if (!warehouseId || !budgetItemId) return;
    const cacheKey = `${warehouseId}:${budgetItemId}`;
    if (batchCache[cacheKey]) return;
    try {
      const { data } = await getAvailableBatches({
        warehouse: warehouseId,
        budget_item: budgetItemId,
      });
      setBatchCache((prev) => ({ ...prev, [cacheKey]: data?.batches || [] }));
    } catch (error) {
      message.warning('Unable to load batches for the selected item.');
    }
  };

  const refreshSerials = async (warehouseId, budgetItemId) => {
    if (!warehouseId || !budgetItemId) return;
    const cacheKey = `${warehouseId}:${budgetItemId}`;
    if (serialCache[cacheKey]) return;
    try {
      const { data } = await getAvailableSerials({
        warehouse: warehouseId,
        budget_item: budgetItemId,
      });
      setSerialCache((prev) => ({ ...prev, [cacheKey]: data?.serial_numbers || [] }));
    } catch (error) {
      message.warning('Unable to load serial numbers for the selected item.');
    }
  };
  const handleSaveIssue = async () => {
    try {
      const values = await form.validateFields();
      const linkedRequisitionIds = values.linked_requisitions || [];
      const missingUoms = [];
      const linesPayload = (values.lines || [])
        .map((line) => {
          const budgetItemId = line.budget_item || null;
          const defaults = getBudgetItemDefaults(budgetItemId);
          const quantityRequested = Number(line.quantity_requested || 0);
          if (!budgetItemId || quantityRequested <= 0) {
            return null;
          }
          const normalizedUom = line.uom || defaults.uomId;
          if (!normalizedUom) {
            missingUoms.push(budgetItemId);
          }
          return {
            id: line.id,
            budget_item: budgetItemId,
            quantity_requested: quantityRequested,
            quantity_issued:
              Number(line.quantity_issued || line.quantity_requested || quantityRequested || 0) || 0,
            uom: normalizedUom,
            batch_lot: line.batch_lot || null,
            serial_numbers: (line.serial_numbers || []).map((serial) => formatSerialValue(serial)),
            cost_center: line.cost_center || values.cost_center || null,
            project: line.project || values.project || null,
            notes: line.notes || '',
            unit_cost: Number(line.unit_cost ?? defaults.valuationRate ?? 0) || 0,
          };
        })
        .filter(Boolean);

      if (!linesPayload.length) {
        message.warning('Add at least one valid line item.');
        return;
      }

      if (missingUoms.length) {
        const missingLabels = missingUoms.map((id) => {
          const record = budgetItemMap[String(id)];
          return record?.code || id;
        });
        message.error(
          `Some selected items are missing stock UOMs. Please update these items before issuing: ${missingLabels.join(
            ', '
          )}`
        );
        return;
      }

      const payload = {
        issue_type: values.issue_type,
        warehouse: values.warehouse,
        cost_center: values.cost_center || null,
        project: values.project || null,
        department: values.department || '',
        issue_date: values.issue_date
          ? values.issue_date.format('YYYY-MM-DD')
          : dayjs().format('YYYY-MM-DD'),
        purpose: values.purpose,
        notes: values.notes || '',
        lines: linesPayload,
        requisition: linkedRequisitionIds[0] || null,
      };

      setSaveLoading(true);
      if (editingIssue) {
        await updateMaterialIssue(editingIssue.id, payload);
        message.success('Material issue updated.');
      } else {
        await createMaterialIssue(payload);
        message.success('Material issue created.');
      }
      closeDrawer();
      await loadIssues();
    } catch (error) {
      if (!error?.errorFields) {
        message.error(error?.response?.data?.detail || 'Unable to save material issue.');
      }
    } finally {
      setSaveLoading(false);
    }
  };

  const handleAction = async (action, record, extraPayload = {}) => {
    setActionLoading((prev) => ({ ...prev, [record.id]: true }));
    try {
      if (action === 'submit') {
        await submitMaterialIssue(record.id);
        message.success('Material issue submitted.');
      } else if (action === 'approve') {
        await approveMaterialIssue(record.id);
        message.success('Material issue approved.');
      } else if (action === 'issue') {
        await issueMaterial(record.id);
        message.success('Materials issued successfully.');
      } else if (action === 'cancel') {
        await cancelMaterialIssue(record.id, extraPayload);
        message.success('Material issue cancelled.');
      }
      await loadIssues();
      if (detailDrawer.visible && detailDrawer.record?.id === record.id) {
        const { data } = await getMaterialIssue(record.id);
        setDetailDrawer((prev) => ({ ...prev, record: data }));
      }
    } catch (error) {
      message.error(error?.response?.data?.message || 'Action failed.');
    } finally {
      setActionLoading((prev) => ({ ...prev, [record.id]: false }));
    }
  };

  const openDetailDrawer = async (record) => {
    setDetailDrawer({ visible: true, record: null, loading: true });
    try {
      const { data } = await getMaterialIssue(record.id);
      setDetailDrawer({ visible: true, record: data, loading: false });
    } catch (error) {
      message.error('Unable to load material issue detail.');
      setDetailDrawer({ visible: false, record: null, loading: false });
    }
  };

  const closeDetailDrawer = () => {
    setDetailDrawer({ visible: false, record: null, loading: false });
  };

  const openCancelModal = (record) => {
    cancelForm.resetFields();
    setCancelModal({ visible: true, record, loading: false });
  };

  const handleConfirmCancel = async () => {
    try {
      const values = await cancelForm.validateFields();
      setCancelModal((prev) => ({ ...prev, loading: true }));
      await handleAction('cancel', cancelModal.record, { reason: values.reason });
      setCancelModal({ visible: false, record: null, loading: false });
      cancelForm.resetFields();
    } catch (error) {
      if (!error?.errorFields) {
        setCancelModal((prev) => ({ ...prev, loading: false }));
      }
    }
  };

  const renderStatusTag = (status) => {
    const metadata = STATUS_TAGS[status] || { color: 'default', text: status || 'Unknown' };
    return <Tag color={metadata.color}>{metadata.text}</Tag>;
  };

  const canEdit = (status) => status === 'DRAFT';
  const canSubmit = (status) => status === 'DRAFT';
  const canApprove = (status) => status === 'SUBMITTED';
  const canIssue = (status) => status === 'APPROVED';
  const canCancel = (status) => !['ISSUED', 'CLOSED'].includes(status);

  const tableColumns = [
    {
      title: 'Issue',
      dataIndex: 'issue_number',
      render: (value, record) => (
        <Space direction="vertical" size={2}>
          <strong>{value || record.reference || `MI-${record.id}`}</strong>
          <Text type="secondary">{record.issue_type || '--'}</Text>
        </Space>
      ),
    },
    {
      title: 'Warehouse',
      dataIndex: 'warehouse_name',
      render: (_, record) =>
        record.warehouse_name ||
        record.warehouse?.name ||
        record.warehouse?.code ||
        record.warehouse ||
        '--',
    },
    {
      title: 'Destination',
      dataIndex: 'destination',
      render: (_, record) =>
        record.project_name ||
        record.project?.name ||
        record.cost_center_name ||
        record.cost_center?.name ||
        record.department ||
        '--',
    },
    {
      title: 'Purpose',
      dataIndex: 'purpose',
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (status) => renderStatusTag(status),
    },
    {
      title: 'Issue Date',
      dataIndex: 'issue_date',
      render: (value) => (value ? dayjs(value).format('MMM D, YYYY') : '--'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small" wrap>
          <Tooltip title="View details">
            <Button icon={<EyeOutlined />} size="small" onClick={() => openDetailDrawer(record)} />
          </Tooltip>
          {canEdit(record.status) && (
            <Tooltip title="Edit">
              <Button icon={<EditOutlined />} size="small" onClick={() => openEditDrawer(record)} />
            </Tooltip>
          )}
          {canSubmit(record.status) && (
            <Tooltip title="Submit for approval">
              <Button
                icon={<SendOutlined />}
                size="small"
                loading={actionLoading[record.id]}
                onClick={() => handleAction('submit', record)}
              />
            </Tooltip>
          )}
          {canApprove(record.status) && (
            <Tooltip title="Approve">
              <Button
                icon={<CheckCircleOutlined />}
                size="small"
                loading={actionLoading[record.id]}
                onClick={() => handleAction('approve', record)}
              />
            </Tooltip>
          )}
          {canIssue(record.status) && (
            <Tooltip title="Issue materials">
              <Button
                type="primary"
                icon={<SendOutlined />}
                size="small"
                loading={actionLoading[record.id]}
                onClick={() => handleAction('issue', record)}
              />
            </Tooltip>
          )}
          {canCancel(record.status) && (
            <Tooltip title="Cancel">
              <Button
                danger
                icon={<CloseCircleOutlined />}
                size="small"
                loading={actionLoading[record.id]}
                onClick={() => openCancelModal(record)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const detailIssue = detailDrawer.record;
  const detailLines = detailIssue?.lines || [];
  const workflowHistory =
    (detailIssue?.history && Array.isArray(detailIssue.history) && detailIssue.history) ||
    (detailIssue?.workflow_log &&
      Array.isArray(detailIssue.workflow_log) &&
      detailIssue.workflow_log) ||
    [];

  const detailLineColumns = [
    {
      title: 'Item',
      dataIndex: 'budget_item',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.budget_item_name || record.budget_item_code || record.budget_item}</Text>
          <Text type="secondary">{record.budget_item_code || record.budget_item}</Text>
        </Space>
      ),
    },
    {
      title: 'Quantity Requested',
      dataIndex: 'quantity_requested',
      render: (value, record) => `${value ?? record.quantity ?? 0} ${record.uom || ''}`.trim(),
    },
    {
      title: 'Quantity Issued',
      dataIndex: 'quantity_issued',
      render: (value, record) => `${value ?? 0} ${record.uom || ''}`.trim(),
    },
    {
      title: 'Batch',
      dataIndex: 'batch_lot',
      render: (value) => value || '--',
    },
    {
      title: 'Serial Numbers',
      dataIndex: 'serial_numbers',
      render: (value) => (Array.isArray(value) && value.length ? value.join(', ') : '--'),
    },
    {
      title: 'Cost Center / Project',
      dataIndex: 'allocation',
      render: (_, record) =>
        record.cost_center_name ||
        record.project_name ||
        record.cost_center ||
        record.project ||
        '--',
    },
  ];
  return (
    <>
      <Card
        title="Material Issue Management"
        extra={
          <Space>
            <Segmented
              options={STATUS_OPTIONS}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
            />
            <Button icon={<ReloadOutlined />} onClick={loadIssues}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreateDrawer}>
              New Issue
            </Button>
          </Space>
        }
      >
        <Table
          rowKey={(record) => record.id || record.issue_number || record.reference}
          columns={tableColumns}
          dataSource={issues}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
      <Drawer
        title={editingIssue ? 'Edit Material Issue' : 'New Material Issue'}
        width={960}
        open={drawerOpen}
        onClose={closeDrawer}
        destroyOnClose
        extra={
          <Space>
            <Button onClick={closeDrawer}>Cancel</Button>
            <Button type="primary" loading={saveLoading} onClick={handleSaveIssue}>
              {editingIssue ? 'Update & Save' : 'Create Issue'}
            </Button>
          </Space>
        }
      >
        <Spin spinning={referenceLoading || requisitionSyncing}>
          <Form layout="vertical" form={form}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="issue_type"
                  label="Issue Type"
                  rules={[{ required: true, message: 'Select issue type' }]}
                >
                  <Select options={ISSUE_TYPE_OPTIONS} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="warehouse"
                  label="Warehouse"
                  rules={[{ required: true, message: 'Select a warehouse' }]}
                >
                  <Select
                    options={warehouseOptions}
                    showSearch
                    placeholder="Select warehouse"
                    optionFilterProp="label"
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="issue_date"
                  label="Issue Date"
                  rules={[{ required: true, message: 'Select issue date' }]}
                >
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="cost_center" label="Cost Center">
                  <Select
                    options={costCenterOptions}
                    showSearch
                    placeholder="Default cost center"
                    optionFilterProp="label"
                    allowClear
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="project" label="Project">
                  <Select
                    options={projectOptions}
                    showSearch
                    placeholder="Default project"
                    optionFilterProp="label"
                    allowClear
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="department" label="Department / Destination">
                  <Input placeholder="Department, production line, etc." />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="purpose"
                  label="Purpose"
                  rules={[{ required: true, message: 'Describe the purpose' }]}
                >
                  <TextArea rows={2} maxLength={300} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="notes" label="Notes">
                  <TextArea rows={2} maxLength={300} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={24}>
                <Form.Item name="linked_requisitions" label="Internal Requisitions">
                  <Select
                    mode="multiple"
                    placeholder="Optional: pull lines from one or more approved IRs"
                    loading={requisitionListLoading}
                    onChange={handleLinkedRequisitionChange}
                    optionFilterProp="label"
                    allowClear
                    showSearch
                  >
                    {requisitionOptions.map((option) => (
                      <Option key={option.value} value={option.value} label={option.label}>
                        <Space direction="vertical" size={0}>
                          <Text strong>{option.label}</Text>
                          <Text type="secondary">{option.description}</Text>
                        </Space>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Divider orientation="left">Line Items</Divider>
            <Form.List name="lines">
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field, index) => {
                    const line = lines[index] || {};
                    const warehouseId = form.getFieldValue('warehouse');
                    const cacheKey =
                      line.budget_item && warehouseId
                        ? `${warehouseId}:${line.budget_item}`
                        : null;
                    const batches = cacheKey ? batchCache[cacheKey] || [] : [];
                    const serials = cacheKey ? serialCache[cacheKey] || [] : [];
                    const estimatedCost = getLineCost(line);

                    return (
                      <Card
                        key={field.key}
                        size="small"
                        style={{ marginBottom: 16 }}
                        title={`Line ${index + 1}`}
                        extra={
                          <Button
                            icon={<StopOutlined />}
                            type="text"
                            danger
                            onClick={() => remove(field.name)}
                          />
                        }
                      >
                        <Row gutter={12}>
                          <Col span={12}>
                            <Form.Item
                              name={[field.name, 'budget_item']}
                              label="Item"
                              rules={[{ required: true, message: 'Select budget item' }]}
                            >
                              <Select
                                options={budgetItemOptions}
                                showSearch
                                placeholder="Search budget item"
                                optionFilterProp="label"
                                onChange={(value) => {
                                  updateLineField(index, {
                                    budget_item: value,
                                    batch_lot: null,
                                    serial_numbers: [],
                                  });
                                  handleBudgetItemSelect(value, index);
                                  if (warehouseId) {
                                    refreshBatches(warehouseId, value);
                                    refreshSerials(warehouseId, value);
                                  }
                                }}
                              />
                            </Form.Item>
                          </Col>
                          <Col span={4}>
                            <Form.Item name={[field.name, 'uom']} hidden>
                              <Input />
                            </Form.Item>
                            <Form.Item label="UOM">
                              <Input
                                disabled
                                placeholder="Auto"
                                value={getLineUomLabel(line) || ''}
                              />
                            </Form.Item>
                          </Col>
                          <Col span={4}>
                            <Form.Item
                              name={[field.name, 'quantity_requested']}
                              label="Qty Requested"
                              rules={[{ required: true, message: 'Qty required' }]}
                            >
                              <InputNumber
                                min={0.01}
                                precision={3}
                                style={{ width: '100%' }}
                                onChange={(value) =>
                                  updateLineField(index, { quantity_issued: value })
                                }
                              />
                            </Form.Item>
                          </Col>
                        </Row>
                        <Row gutter={12}>
                          <Col span={8}>
                            <Form.Item name={[field.name, 'batch_lot']} label="Batch / Lot">
                              <Select
                                showSearch
                                placeholder="Select batch"
                                optionFilterProp="label"
                                options={batches.map((batch) => ({
                                  value:
                                    batch.id ||
                                    batch.batch_no ||
                                    batch.batch_code ||
                                    batch.lot ||
                                    batch.name,
                                  label: formatBatchLabel(batch),
                                }))}
                                onDropdownVisibleChange={(open) => {
                                  if (open && warehouseId && line.budget_item) {
                                    refreshBatches(warehouseId, line.budget_item);
                                  }
                                }}
                                allowClear
                              />
                            </Form.Item>
                          </Col>
                          <Col span={8}>
                            <Form.Item name={[field.name, 'serial_numbers']} label="Serial Numbers">
                              <Select
                                mode="multiple"
                                placeholder="Select serials"
                                optionFilterProp="label"
                                options={serials.map((serial) => ({
                                  value: formatSerialValue(serial),
                                  label:
                                    serial.serial ||
                                    serial.serial_no ||
                                    serial.code ||
                                    formatSerialValue(serial),
                                }))}
                                onDropdownVisibleChange={(open) => {
                                  if (open && warehouseId && line.budget_item) {
                                    refreshSerials(warehouseId, line.budget_item);
                                  }
                                }}
                              />
                            </Form.Item>
                          </Col>
                          <Col span={8}>
                            <Form.Item name={[field.name, 'cost_center']} label="Line Cost Center">
                              <Select
                                options={costCenterOptions}
                                showSearch
                                optionFilterProp="label"
                                placeholder="Override cost center"
                                allowClear
                              />
                            </Form.Item>
                          </Col>
                        </Row>
                        <Row gutter={12}>
                          <Col span={8}>
                            <Form.Item name={[field.name, 'project']} label="Line Project">
                              <Select
                                options={projectOptions}
                                showSearch
                                optionFilterProp="label"
                                placeholder="Override project"
                                allowClear
                              />
                            </Form.Item>
                          </Col>
                          <Col span={16}>
                            <Form.Item name={[field.name, 'notes']} label="Line Notes">
                              <Input placeholder="Special instructions" />
                            </Form.Item>
                          </Col>
                        </Row>
                        <Row>
                          <Col span={24}>
                            <Text type="secondary">
                              Estimated Cost:{' '}
                              <Text strong>
                                {estimatedCost ? `${estimatedCost.toFixed(2)} (approx)` : '--'}
                              </Text>
                            </Text>
                          </Col>
                        </Row>
                        <Form.Item name={[field.name, 'id']} hidden>
                          <Input type="hidden" />
                        </Form.Item>
                      </Card>
                    );
                  })}
                  <Button
                    type="dashed"
                    block
                    icon={<PlusOutlined />}
                    onClick={() => add({ quantity_requested: 1 })}
                  >
                    Add Line
                  </Button>
                </>
              )}
            </Form.List>
            <Divider />
            <div style={{ textAlign: 'right' }}>
              <Text type="secondary">Estimated Total Cost</Text>
              <div>
                <Text strong style={{ fontSize: 18 }}>
                  {totalEstimatedCost ? totalEstimatedCost.toFixed(2) : '--'}
                </Text>
              </div>
            </div>
          </Form>
        </Spin>
      </Drawer>
      <Drawer
        title={
          detailIssue
            ? `Material Issue ${
                detailIssue.issue_number || detailIssue.reference || detailIssue.id
              }`
            : 'Material Issue Detail'
        }
        width={720}
        open={detailDrawer.visible}
        onClose={closeDetailDrawer}
      >
        <Spin spinning={detailDrawer.loading}>
          {detailIssue ? (
            <>
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="Issue Type">
                  {detailIssue.issue_type || '--'}
                </Descriptions.Item>
                <Descriptions.Item label="Status">
                  {renderStatusTag(detailIssue.status)}
                </Descriptions.Item>
                <Descriptions.Item label="Warehouse">
                  {detailIssue.warehouse_name ||
                    detailIssue.warehouse?.name ||
                    detailIssue.warehouse ||
                    '--'}
                </Descriptions.Item>
                <Descriptions.Item label="Destination">
                  {detailIssue.project_name ||
                    detailIssue.project?.name ||
                    detailIssue.cost_center_name ||
                    detailIssue.cost_center?.name ||
                    detailIssue.department ||
                    '--'}
                </Descriptions.Item>
                <Descriptions.Item label="Issue Date" span={2}>
                  {detailIssue.issue_date
                    ? dayjs(detailIssue.issue_date).format('MMM D, YYYY')
                    : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="Purpose" span={2}>
                  {detailIssue.purpose || '--'}
                </Descriptions.Item>
                <Descriptions.Item label="Notes" span={2}>
                  {detailIssue.notes || '--'}
                </Descriptions.Item>
              </Descriptions>
              <Divider />
              <Tabs
                items={[
                  {
                    key: 'lines',
                    label: `Lines (${detailLines.length})`,
                    children: (
                      <Table
                        rowKey={(record) => record.id || `${record.budget_item}-${record.batch_lot}`}
                        columns={detailLineColumns}
                        dataSource={detailLines}
                        pagination={false}
                        size="small"
                      />
                    ),
                  },
                  {
                    key: 'history',
                    label: 'Approval History',
                    children: workflowHistory.length ? (
                      <Timeline
                        items={workflowHistory.map((entry) => ({
                          color:
                            entry.status === 'APPROVED'
                              ? 'green'
                              : entry.status === 'REJECTED'
                              ? 'red'
                              : 'blue',
                          children: (
                            <Space direction="vertical" size={0}>
                              <Text strong>{entry.status || entry.action}</Text>
                              <Text>{entry.actor || entry.user || entry.performed_by || '--'}</Text>
                              <Text type="secondary">
                                {entry.timestamp || entry.created_at
                                  ? dayjs(entry.timestamp || entry.created_at).format(
                                      'MMM D, YYYY HH:mm'
                                    )
                                  : ''}
                              </Text>
                              {entry.comment ? <Text>{entry.comment}</Text> : null}
                            </Space>
                          ),
                        }))}
                      />
                    ) : (
                      <Empty description="No approval history yet" />
                    ),
                  },
                ]}
              />
            </>
          ) : (
            <Empty description="Select a material issue to view details" />
          )}
        </Spin>
      </Drawer>
      <Modal
        title="Cancel Material Issue"
        open={cancelModal.visible}
        confirmLoading={cancelModal.loading}
        onCancel={() => setCancelModal({ visible: false, record: null, loading: false })}
        onOk={handleConfirmCancel}
      >
        <Form layout="vertical" form={cancelForm}>
          <Form.Item
            name="reason"
            label="Reason"
            rules={[{ required: true, message: 'Please enter a reason' }]}
          >
            <TextArea rows={3} maxLength={200} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default MaterialIssueManagement;
