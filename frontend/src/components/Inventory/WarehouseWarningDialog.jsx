import React, { useState } from 'react';
import { Modal, Alert, Input, Select, Button, Space, Typography, Tag, Divider } from 'antd';
import { WarningOutlined, InfoCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Text, Title } = Typography;

/**
 * WarehouseWarningDialog Component
 *
 * Displays a warning when user selects a warehouse that doesn't match
 * the configured warehouse for the item's category/subcategory.
 *
 * Props:
 * - visible: boolean - Whether the dialog is visible
 * - validation: object - Validation result from API
 *   {
 *     is_valid: boolean,
 *     warning_level: 'INFO' | 'WARNING' | 'CRITICAL',
 *     message: string,
 *     requires_reason: boolean,
 *     requires_approval: boolean,
 *     suggested_warehouse: { id, code, name },
 *     allowed_warehouses: [...]
 *   }
 * - onConfirm: function(reason, approvedBy) - Called when user confirms override
 * - onCancel: function() - Called when user cancels
 * - onUseSuggested: function() - Called when user chooses suggested warehouse
 */
const WarehouseWarningDialog = ({
  visible,
  validation,
  onConfirm,
  onCancel,
  onUseSuggested,
  supervisors = []  // List of supervisors for approval
}) => {
  const [reason, setReason] = useState('');
  const [approvedBy, setApprovedBy] = useState(null);
  const [loading, setLoading] = useState(false);

  // Reset form when dialog opens/closes
  React.useEffect(() => {
    if (!visible) {
      setReason('');
      setApprovedBy(null);
    }
  }, [visible]);

  if (!validation) {
    return null;
  }

  const {
    is_valid,
    warning_level,
    message,
    requires_reason,
    requires_approval,
    suggested_warehouse,
    allowed_warehouses = []
  } = validation;

  // Get icon and color based on warning level
  const getWarningConfig = () => {
    switch (warning_level) {
      case 'CRITICAL':
        return {
          icon: <CloseCircleOutlined />,
          color: 'error',
          tagColor: 'red'
        };
      case 'WARNING':
        return {
          icon: <WarningOutlined />,
          color: 'warning',
          tagColor: 'orange'
        };
      case 'INFO':
      default:
        return {
          icon: <InfoCircleOutlined />,
          color: 'info',
          tagColor: 'blue'
        };
    }
  };

  const { icon, color, tagColor } = getWarningConfig();

  // Predefined reasons for quick selection
  const predefinedReasons = [
    'Urgent requirement - suggested warehouse not available',
    'Customer request for specific warehouse',
    'Suggested warehouse at capacity',
    'Stock consolidation requirement',
    'Temporary relocation for maintenance',
    'Other (specify below)'
  ];

  const handleConfirm = async () => {
    // Validate inputs
    if (requires_reason && !reason) {
      Modal.error({
        title: 'Reason Required',
        content: 'Please provide a reason for selecting a different warehouse.'
      });
      return;
    }

    if (requires_approval && !approvedBy) {
      Modal.error({
        title: 'Approval Required',
        content: 'This is a critical warning. Supervisor approval is required.'
      });
      return;
    }

    setLoading(true);
    try {
      await onConfirm(reason, approvedBy);
    } finally {
      setLoading(false);
    }
  };

  const handleUseSuggested = () => {
    if (onUseSuggested && suggested_warehouse) {
      onUseSuggested(suggested_warehouse);
    }
  };

  return (
    <Modal
      open={visible}
      title={
        <Space>
          {icon}
          <span>Warehouse Selection Warning</span>
          <Tag color={tagColor}>{warning_level}</Tag>
        </Space>
      }
      onCancel={onCancel}
      width={600}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          Cancel
        </Button>,
        suggested_warehouse && (
          <Button key="suggested" type="default" onClick={handleUseSuggested}>
            Use Suggested: {suggested_warehouse.code}
          </Button>
        ),
        <Button
          key="confirm"
          type="primary"
          danger={warning_level === 'CRITICAL'}
          loading={loading}
          onClick={handleConfirm}
        >
          Proceed with Selection
        </Button>
      ]}
    >
      {/* Warning Message */}
      <Alert
        message={message}
        type={color}
        showIcon
        icon={icon}
        style={{ marginBottom: 16 }}
      />

      {/* Suggested Warehouse */}
      {suggested_warehouse && (
        <>
          <div style={{ marginBottom: 16 }}>
            <Text strong>Suggested Warehouse:</Text>
            <div style={{
              padding: '8px 12px',
              background: '#e6f7ff',
              borderRadius: '4px',
              marginTop: '8px'
            }}>
              <Space>
                <Text strong>{suggested_warehouse.code}</Text>
                <Text type="secondary">-</Text>
                <Text>{suggested_warehouse.name}</Text>
              </Space>
            </div>
          </div>
          <Divider />
        </>
      )}

      {/* Allowed Warehouses */}
      {allowed_warehouses.length > 0 && (
        <>
          <div style={{ marginBottom: 16 }}>
            <Text strong>Allowed Warehouses for this Item:</Text>
            <div style={{ marginTop: 8 }}>
              {allowed_warehouses.map((wh) => (
                <Tag key={wh.id} color="blue" style={{ marginBottom: 4 }}>
                  {wh.code} - {wh.name}
                </Tag>
              ))}
            </div>
          </div>
          <Divider />
        </>
      )}

      {/* Override Reason - Required for WARNING and CRITICAL */}
      {requires_reason && (
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ color: '#ff4d4f' }}>
            * Reason for Override (Required):
          </Text>
          <Select
            placeholder="Select a predefined reason or choose 'Other'"
            style={{ width: '100%', marginTop: 8, marginBottom: 8 }}
            value={predefinedReasons.includes(reason) ? reason : predefinedReasons.find(r => r.startsWith('Other')) ? 'Other' : undefined}
            onChange={(value) => {
              if (value !== 'Other (specify below)') {
                setReason(value);
              } else {
                setReason('');
              }
            }}
            options={predefinedReasons.map((r) => ({
              label: r,
              value: r
            }))}
          />
          <TextArea
            placeholder="Provide additional details or specify your reason here..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            maxLength={500}
            showCount
          />
        </div>
      )}

      {/* Supervisor Approval - Required for CRITICAL */}
      {requires_approval && (
        <div style={{ marginBottom: 16 }}>
          <Alert
            message="Supervisor Approval Required"
            description="This selection requires supervisor approval due to critical mismatch with configured warehouse."
            type="error"
            showIcon
            style={{ marginBottom: 12 }}
          />
          <Text strong style={{ color: '#ff4d4f' }}>
            * Approved By (Required):
          </Text>
          <Select
            placeholder="Select supervisor who approved this override"
            style={{ width: '100%', marginTop: 8 }}
            value={approvedBy}
            onChange={setApprovedBy}
            showSearch
            optionFilterProp="label"
            options={supervisors.map((sup) => ({
              label: `${sup.username} - ${sup.first_name} ${sup.last_name}`,
              value: sup.id
            }))}
          />
          <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
            The selected supervisor must have authorized this warehouse override.
          </Text>
        </div>
      )}

      {/* Info Note */}
      <Alert
        message="Note"
        description="This override will be logged for audit purposes. Please ensure you have a valid reason for selecting a different warehouse."
        type="info"
        showIcon
        style={{ marginTop: 16 }}
      />
    </Modal>
  );
};

export default WarehouseWarningDialog;
