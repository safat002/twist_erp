import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Avatar,
  Badge,
  Button,
  Card,
  Drawer,
  Divider,
  Form,
  Input,
  List,
  Modal,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message as toast,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  DislikeOutlined,
  LikeOutlined,
  ReloadOutlined,
  RobotOutlined,
  SendOutlined,
  SettingOutlined,
  EditOutlined,
  ThunderboltOutlined,
  UserOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import api from '../../services/api';
import { useNavigate } from 'react-router-dom';
import {
  chatWithAI,
  deleteAIPreference,
  executeAIAction,
  fetchAIConversationHistory,
  fetchAISuggestions,
  fetchAIPreferences,
  saveAIPreference,
  sendAIFeedback,
  trainAI,
  updateAISuggestion,
  fetchAIAgenda,
} from '../../services/ai';
import { useCompany } from '../../contexts/CompanyContext';

const { Text } = Typography;
const CONVERSATION_STORAGE_KEY = 'twist_erp.ai_conversation_id';
const severityColors = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};
const formatTimestamp = (value) => {
  if (!value) return '';
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return String(value);
  }
};

const AIWidget = () => {
  const { currentCompany } = useCompany();
  const navigate = useNavigate();
  const [visible, setVisible] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const [suggestions, setSuggestions] = useState([]);
  const [agenda, setAgenda] = useState(null);
  const [feedbackSending, setFeedbackSending] = useState(false);
  const [historyHydrated, setHistoryHydrated] = useState(false);
  const [preferences, setPreferences] = useState([]);
  const [prefModalVisible, setPrefModalVisible] = useState(false);
  const [prefLoading, setPrefLoading] = useState(false);
  const [editingPreference, setEditingPreference] = useState(null);
  const [pendingAction, setPendingAction] = useState(null);
  const [actionModalVisible, setActionModalVisible] = useState(false);
  const [actionExecuting, setActionExecuting] = useState(false);
  const [prefForm] = Form.useForm();
  const messagesEndRef = useRef(null);
  const pollingRef = useRef(null);
  const lastUnreadRef = useRef(0);
  const hydratedUnreadRef = useRef(false);
  const [pulse, setPulse] = useState(false);

  const loadUnreadAlerts = useCallback(async () => {
    try {
      const { data } = await api.get('/api/v1/ai/alerts/unread-count/');
      const count = Number(
        data?.count ?? data?.unread ?? data?.total ?? data?.unread_count ?? 0,
      );
      const safeCount = Number.isFinite(count) ? count : 0;
      if (hydratedUnreadRef.current) {
        if (safeCount > (lastUnreadRef.current || 0)) {
          setPulse(true);
          window.setTimeout(() => setPulse(false), 3000);
        }
      } else {
        hydratedUnreadRef.current = true;
      }
      lastUnreadRef.current = safeCount;
      setUnreadAlerts(safeCount);
    } catch (error) {
      if (error?.response?.status === 401) {
        setUnreadAlerts(0);
      } else {
        // avoid noisy toasts during idle polling
        console.warn('Failed to load AI unread alerts', error);
      }
    }
  }, [currentCompany?.id]);

  const loadSuggestions = useCallback(async () => {
    try {
      const { data } = await fetchAISuggestions({ limit: 20 });
      setSuggestions(data?.results || data || []);
    } catch (error) {
      console.warn('Failed to load AI suggestions', error);
    }
  }, []);

  const loadAgenda = useCallback(async () => {
    try {
      const { data } = await fetchAIAgenda();
      setAgenda(data || null);
    } catch (error) {
      console.warn('Failed to load AI agenda', error);
    }
  }, []);

  useEffect(() => {
    try {
      const storedConversationId = window.localStorage.getItem(CONVERSATION_STORAGE_KEY);
      if (storedConversationId) {
        setConversationId(storedConversationId);
      }
    } catch (error) {
      // Ignore storage access errors
    }
  }, []);

  useEffect(() => {
    loadUnreadAlerts();
    const intervalId = setInterval(loadUnreadAlerts, 60000);
    pollingRef.current = intervalId;
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      pollingRef.current = null;
    };
  }, [loadUnreadAlerts]);

  useEffect(() => {
    if (visible) {
      loadSuggestions();
      loadAgenda();
      if (!historyHydrated) {
        hydrateConversation();
      }
    }
  }, [visible, historyHydrated, conversationId, loadSuggestions, loadAgenda]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadPreferences = useCallback(
    async (withSpinner = true) => {
      if (withSpinner) {
        setPrefLoading(true);
      }
      try {
        const { data } = await fetchAIPreferences();
        setPreferences(data?.results || []);
      } catch (error) {
        toast.error(error?.response?.data?.detail || 'Unable to load AI preferences.');
      } finally {
        if (withSpinner) {
          setPrefLoading(false);
        }
      }
    },
    [],
  );

  useEffect(() => {
    if (prefModalVisible) {
      loadPreferences();
    } else {
      setEditingPreference(null);
      prefForm.resetFields();
    }
  }, [prefModalVisible, loadPreferences, prefForm]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const hydrateConversation = async () => {
    try {
      const { data } = await fetchAIConversationHistory({
        conversationId,
        limit: 200,
      });
      if (data?.conversation?.id) {
        const resolvedConversationId = data.conversation.id;
        if (!conversationId || conversationId !== resolvedConversationId) {
          setConversationId(resolvedConversationId);
        }
        try {
          window.localStorage.setItem(CONVERSATION_STORAGE_KEY, resolvedConversationId);
        } catch (error) {
          // ignore storage failures
        }
        const hydrated = (data.messages || []).map((msg) => {
          const metadata = msg.metadata || {};
          return {
            role: msg.role,
            content: msg.content,
            intent: msg.intent,
            confidence: msg.confidence,
            sources: metadata.sources || [],
            actions: metadata.actions || [],
            skill: metadata.skill,
            context: metadata.context,
            timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
          };
        });
        setMessages(hydrated);
      } else if (!conversationId) {
        setMessages([]);
      }
    } catch (error) {
      // allow user to continue chatting even if history load fails
    } finally {
      setHistoryHydrated(true);
    }
  };

  const handlePreferenceSave = async () => {
    try {
      const values = await prefForm.validateFields();
      let parsedValue = values.value;
      if (typeof parsedValue === 'string') {
        const trimmed = parsedValue.trim();
        if (!trimmed.length) {
          parsedValue = '';
        } else {
          try {
            parsedValue = JSON.parse(trimmed);
          } catch (error) {
            parsedValue = trimmed;
          }
        }
      }
      const payload = {
        id: editingPreference?.id,
        key: values.key,
        value: parsedValue,
        scope: values.scope || 'company',
      };
      setPrefLoading(true);
      await saveAIPreference(payload);
      toast.success('Preference saved');
      setEditingPreference(null);
      prefForm.resetFields();
      await loadPreferences(false);
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      toast.error(error?.response?.data?.detail || 'Unable to save preference');
    } finally {
      setPrefLoading(false);
    }
  };

  const handlePreferenceDelete = async (id) => {
    setPrefLoading(true);
    try {
      await deleteAIPreference(id);
      toast.success('Preference removed');
      await loadPreferences(false);
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Unable to delete preference');
    } finally {
      setPrefLoading(false);
    }
  };

  const handleEditPreference = (item) => {
    setEditingPreference(item);
    setPrefModalVisible(true);
    prefForm.setFieldsValue({
      key: item.key,
      value:
        typeof item.value === 'object' && item.value !== null
          ? JSON.stringify(item.value, null, 2)
          : item.value,
      scope: item.scope === 'global' ? 'global' : 'company',
    });
  };

  const resetConversation = () => {
    setConversationId(null);
    setMessages([]);
    setHistoryHydrated(false);
    try {
      window.localStorage.removeItem(CONVERSATION_STORAGE_KEY);
    } catch (error) {
      // ignore storage failures
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const trimmed = input.trim();
    if (trimmed.toLowerCase().startsWith('/remember ')) {
      const note = trimmed.slice(10).trim();
      try {
        await trainAI({ key: `note:${Date.now()}`, value: { note } });
        toast.success('Saved to AI memory');
      } catch (error) {
        toast.error('Unable to save memory');
      } finally {
        setInput('');
      }
      return;
    }

    const userMessage = {
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const { data } = await chatWithAI({
        message: trimmed,
        conversation_id: conversationId,
        context: {
          page: window.location.pathname,
          module: getCurrentModule(),
        },
      });

      setConversationId(data.conversation_id);
      try {
        window.localStorage.setItem(CONVERSATION_STORAGE_KEY, data.conversation_id);
      } catch (error) {
        // ignore storage failures
      }
      setHistoryHydrated(true);

      const assistantMessage = {
        role: 'assistant',
        content: data.message,
        intent: data.intent,
        confidence: data.confidence,
        context: data.context,
        sources: data.sources || [],
        actions: data.actions || [],
        skill: data.skill,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if ((data.suggestions || []).length > 0) {
        await loadSuggestions();
        await loadUnreadAlerts();
      }
    } catch (error) {
      const serverMsg = error?.response?.data?.message;
      const errorMessage = {
        role: 'assistant',
        content: serverMsg || "I'm having trouble responding right now. Please try again in a minute.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const getCurrentModule = () => {
    const path = window.location.pathname;
    if (path.includes('/migration')) return 'data_migration';
    if (path.includes('/analytics')) return 'analytics';
    if (path.includes('/finance')) return 'finance';
    if (path.includes('/inventory')) return 'inventory';
    if (path.includes('/sales')) return 'sales';
    if (path.includes('/policies')) return 'policy';
    return 'general';
  };

  const executeActionDirect = async (actionName, payload) => {
    setActionExecuting(true);
    try {
      const { data } = await executeAIAction({ action: actionName, payload });
      const message = data?.result?.summary || data?.result?.message || 'Action executed.';
      toast.success(message);
      const detailPayload = data?.result?.details;
      if (message || detailPayload) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: message,
            timestamp: new Date(),
            context: detailPayload ? { workflow: detailPayload } : undefined,
          },
        ]);
      }
      await loadSuggestions();
      await loadUnreadAlerts();
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Unable to run action.');
    } finally {
      setActionExecuting(false);
      setActionModalVisible(false);
      setPendingAction(null);
    }
  };

  const handleAction = (action) => {
    if (!action) return;
    if (action.action === 'navigate' && action.payload?.path) {
      navigate(action.payload.path);
      return;
    }
    if (action.action === 'api' && action.payload?.endpoint) {
      api
        .post(action.payload.endpoint)
        .then(() => toast.success('Triggered follow-up action'))
        .catch(() => toast.error('Unable to trigger action'));
      return;
    }
    if (action.action === 'ai.execute') {
      const actionName =
        action.payload?.action_name || action.payload?.action || action.actionName || action.action_name;
      if (!actionName) {
        toast.warning('Unsupported action payload.');
        return;
      }
      const payload =
        action.payload?.parameters || action.payload?.payload || action.payload || {};
      if (action.requires_confirmation) {
        setPendingAction({
          actionName,
          payload,
          confirmationText: action.confirmation_text || action.confirmationText,
          label: action.label,
        });
        setActionModalVisible(true);
      } else {
        executeActionDirect(actionName, payload);
      }
      return;
    }
    toast.info('Action recorded.');
  };

  const handleConfirmAction = () => {
    if (!pendingAction) return;
    executeActionDirect(pendingAction.actionName, pendingAction.payload);
  };

  const handleCancelAction = () => {
    setActionModalVisible(false);
    setPendingAction(null);
  };

  const handleFeedback = async (rating) => {
    if (!conversationId) return;
    setFeedbackSending(true);
    try {
      await sendAIFeedback({ conversationId, rating });
      toast.success('Thanks for the feedback!');
    } catch (error) {
      toast.error('Unable to record feedback');
    } finally {
      setFeedbackSending(false);
    }
  };

  const handleSuggestionDecision = async (suggestionId, status) => {
    try {
      await updateAISuggestion({ suggestionId, status });
      await loadSuggestions();
      await loadUnreadAlerts();
    } catch (error) {
      toast.error('Could not update suggestion');
    }
  };

  const renderActions = (actions = []) => {
    if (!actions.length) return null;
    return (
      <Space wrap style={{ marginTop: 8 }}>
        {actions.map((action) => (
          <Button
            key={`${action.action}-${action.label}`}
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => handleAction(action)}
          >
            {action.label}
          </Button>
        ))}
      </Space>
    );
  };

  const renderContextSummary = (ctx) => {
    if (!ctx) return null;
    const roles = (ctx.short_term && ctx.short_term.user_roles) || [];
    const migrations = (ctx.short_term && ctx.short_term.pending_migrations) || [];
    if (!roles.length && !migrations.length) {
      return null;
    }
    return (
      <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
        {roles.length > 0 && <div>Roles: {roles.join(', ')}</div>}
        {migrations.length > 0 && (
          <div>
            Pending migrations:{' '}
            {migrations.map((item) => item.target || item.migration_job_id || item.job_id).join(', ')}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
        <Badge count={unreadAlerts} overflowCount={99}>
          <Button
            type="primary"
            shape="circle"
            size="large"
            icon={<RobotOutlined />}
            onClick={() => setVisible(true)}
            style={{
              position: 'fixed',
              bottom: 24,
              right: 24,
              width: 60,
              height: 60,
              zIndex: 1000,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            }}
          />
        </Badge>

      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <RobotOutlined style={{ marginRight: 8, fontSize: 20 }} />
            AI Assistant
          </div>
        }
        placement="right"
        width={420}
        onClose={() => setVisible(false)}
        open={visible}
        styles={{ body: { padding: 0 } }}
        destroyOnClose
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {suggestions.length > 0 && (
            <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>Proactive suggestions</Text>
                {suggestions.map((suggestion) => (
                  <Card
                    key={suggestion.id}
                    size="small"
                    title={suggestion.title}
                    extra={(
                      <Space>
                        <Tag color={severityColors[suggestion.severity] || 'blue'}>
                          {String(suggestion.severity || 'info').toUpperCase()}
                        </Tag>
                        <Tag color="purple">
                          {suggestion.alert_type || suggestion.source_skill || 'AI'}
                        </Tag>
                      </Space>
                    )}
                  >
                    <Typography.Paragraph style={{ marginBottom: 12 }}>
                      {suggestion.body}
                    </Typography.Paragraph>
                    {suggestion.metadata?.rule_code === 'metadata.promote_field' ? (
                      <Text type="secondary" style={{ display: 'block' }}>
                        Field:{' '}
                        {suggestion.metadata.field_label || suggestion.metadata.field_name}{' '}
                        Â· {suggestion.metadata.definition_key}
                      </Text>
                    ) : null}
                    {suggestion.metadata?.rule_code === 'metadata.dashboard_widget' ? (
                      <Text type="secondary" style={{ display: 'block' }}>
                        Widget: {suggestion.metadata.widget_id}
                      </Text>
                    ) : null}
                    {suggestion.created_at ? (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatTimestamp(suggestion.created_at)}
                      </Text>
                    ) : null}
                    {suggestion.metadata?.actions?.length ? (
                      <Space wrap style={{ marginTop: 12, marginBottom: 12 }}>
                        {suggestion.metadata.actions.map((action) => (
                          <Button
                            key={`${suggestion.id}-${action.label || action.action}`}
                            size="small"
                            icon={<ThunderboltOutlined />}
                            onClick={() => handleAction(action)}
                          >
                            {action.label || 'Run'}
                          </Button>
                        ))}
                      </Space>
                    ) : null}
                    <Space style={{ marginTop: 8 }}>
                      <Button
                        size="small"
                        type="primary"
                        icon={<CheckOutlined />}
                        onClick={() => handleSuggestionDecision(suggestion.id, 'accepted')}
                      >
                        Accept
                      </Button>
                      <Button
                        size="small"
                        icon={<CloseOutlined />}
                        onClick={() => handleSuggestionDecision(suggestion.id, 'dismissed')}
                      >
                        Dismiss
                      </Button>
                    </Space>
                  </Card>
                ))}
              </Space>
            </div>
          )}

          {agenda && (
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
              <Card size="small" title="My Agenda" extra={
                <Space size={8}>
                  <Tag color="geekblue">Approvals: {agenda.counts?.approvals ?? 0}</Tag>
                  <Tag color="green">Budgets: {agenda.counts?.budgets_due ?? 0}</Tag>
                  <Tag color="orange">GRN: {agenda.counts?.pos_pending_grn ?? 0}</Tag>
                  <Tag color="volcano">AP: {agenda.counts?.ap_due ?? 0}</Tag>
                </Space>
              }>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {(agenda.agenda?.approvals || []).slice(0, 3).map((a, idx) => (
                    <Text key={`appr-${idx}`}>
                      - Approval: {a.workflow} – {a.task_name}
                    </Text>
                  ))}
                  {(agenda.agenda?.budgets_due || []).slice(0, 3).map((b) => (
                    <Text key={`bd-${b.id}`}>
                      - Budget: {b.name} (due {new Date(b.entry_end_date).toLocaleDateString()})
                    </Text>
                  ))}
                  {(agenda.agenda?.pos_pending_grn || []).slice(0, 3).map((p) => (
                    <Text key={`po-${p.id}`}>
                      - PO {p.po_number} – {p['supplier__name']} (ETA {new Date(p.expected_delivery_date).toLocaleDateString()})
                    </Text>
                  ))}
                  {(agenda.agenda?.ap_due || []).slice(0, 3).map((i) => (
                    <Text key={`ap-${i.id}`}>
                      - AP Bill {i.bill_number} – {i['supplier__name']} (due {new Date(i.due_date).toLocaleDateString()})
                    </Text>
                  ))}
                </Space>
              </Card>
            </div>
          )}

          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#aaa', marginTop: '40%' }}>
                <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <div>Hi! I'm your AI assistant.</div>
                <div>Ask about migrations, dashboards, or company policies.</div>
              </div>
            )}
            <List
              dataSource={messages}
              renderItem={(msg) => (
                <List.Item style={{ border: 'none' }}>
                  <List.Item.Meta
                    avatar={<Avatar icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />} />}
                    title={msg.role === 'user' ? 'You' : `AI Assistant${msg.skill ? ` - ${msg.skill}` : ''}`}
                    description={
                      <div>
                        <div>{msg.content}</div>
                        {msg.sources && msg.sources.length > 0 && (
                          <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
                            Sources: {msg.sources.join(', ')}
                          </div>
                        )}
                        {renderActions(msg.actions)}
                        {renderContextSummary(msg.context)}
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
            {loading && (
              <div style={{ textAlign: 'center', padding: 16 }}>
                <Spin />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0' }}>
            <Space style={{ marginBottom: 8, width: '100%', justifyContent: 'space-between' }}>
              <Text type="secondary">Tip: Use /remember to teach me something.</Text>
              <Space>
                <Button
                  size="small"
                  icon={<SettingOutlined />}
                  onClick={() => {
                    setEditingPreference(null);
                    setPrefModalVisible(true);
                    prefForm.setFieldsValue({
                      key: '',
                      value: '',
                      scope: 'company',
                    });
                  }}
                >
                  Preferences
                </Button>
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={resetConversation}
                >
                  New chat
                </Button>
                <Button
                  size="small"
                  icon={<LikeOutlined />}
                  loading={feedbackSending}
                  disabled={!conversationId}
                  onClick={() => handleFeedback('up')}
                />
                <Button
                  size="small"
                  icon={<DislikeOutlined />}
                  loading={feedbackSending}
                  disabled={!conversationId}
                  onClick={() => handleFeedback('down')}
                />
              </Space>
            </Space>
            <Input.Search
              placeholder="Ask me anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onSearch={sendMessage}
              loading={loading}
              enterButton={<SendOutlined />}
              size="large"
            />
          </div>
        </div>
      </Drawer>
      {/* Floating AI button with notification badge (pulses on new alerts) */}
      <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1000 }}>
        <style>{`
          @keyframes aiFabPulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(24, 144, 255, 0.4); }
            50% { transform: scale(1.06); box-shadow: 0 0 0 10px rgba(24, 144, 255, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(24, 144, 255, 0); }
          }
          .ai-fab-pulse {
            animation: aiFabPulse 0.7s ease-in-out;
            animation-iteration-count: 4;
          }
          .ai-fab-pulse .ant-badge-count, .ai-fab-pulse .ant-badge-dot {
            animation: aiFabPulse 0.7s ease-in-out;
            animation-iteration-count: 4;
          }
        `}</style>
        <div className={pulse ? 'ai-fab-pulse' : ''}>
          <Badge
            count={unreadAlerts > 0 ? unreadAlerts : null}
            dot={unreadAlerts === 0}
            overflowCount={99}
            offset={[-4, 6]}
          >
            <Button
              type="primary"
              shape="circle"
              size="large"
              icon={<RobotOutlined />}
              onClick={() => setVisible(true)}
              aria-label="Open AI Assistant"
              style={{ width: 60, height: 60 }}
              title="AI Assistant"
            />
          </Badge>
        </div>
      </div>
      <Modal
        title={pendingAction?.label || 'Confirm action'}
        open={actionModalVisible}
        onCancel={handleCancelAction}
        confirmLoading={actionExecuting}
        onOk={handleConfirmAction}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Text>
            {pendingAction?.confirmationText || 'Are you sure you want to run this action?'}
          </Text>
          {pendingAction?.payload ? (
            <Card size="small" title="Payload">
              <pre style={{ margin: 0, fontSize: 12 }}>
                {JSON.stringify(pendingAction.payload, null, 2)}
              </pre>
            </Card>
          ) : null}
        </Space>
      </Modal>
      <Modal
        title="AI Preferences"
        open={prefModalVisible}
        onCancel={() => {
          setPrefModalVisible(false);
          setEditingPreference(null);
          prefForm.resetFields();
        }}
        footer={null}
        width={520}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Form
            form={prefForm}
            layout="vertical"
            initialValues={{ scope: 'company' }}
            disabled={prefLoading}
          >
            <Form.Item
              label="Preference Key"
              name="key"
              rules={[{ required: true, message: 'Provide a preference key.' }]}
            >
              <Input placeholder="e.g. default_currency" autoComplete="off" />
            </Form.Item>
            <Form.Item
              label="Value"
              name="value"
              rules={[{ required: true, message: 'Provide a value.' }]}
            >
              <Input.TextArea
                placeholder='Supports text or JSON (e.g. {"currency":"BDT"})'
                autoSize={{ minRows: 2, maxRows: 6 }}
              />
            </Form.Item>
            <Form.Item label="Scope" name="scope">
              <Select
                options={[
                  {
                    value: 'company',
                    label: currentCompany
                      ? `Company (${currentCompany.code || currentCompany.name || 'Current'})`
                      : 'Company',
                  },
                  { value: 'global', label: 'Global' },
                ]}
              />
            </Form.Item>
            <Button type="primary" block onClick={handlePreferenceSave} loading={prefLoading}>
              {editingPreference ? 'Update Preference' : 'Save Preference'}
            </Button>
          </Form>
          <Divider style={{ margin: '12px 0' }} />
          <List
            loading={prefLoading && preferences.length === 0}
            dataSource={preferences}
            locale={{ emptyText: 'No preferences yet.' }}
            renderItem={(item) => (
              <List.Item
                key={item.id}
                actions={[
                  <Button
                    key="edit"
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleEditPreference(item)}
                  >
                    Edit
                  </Button>,
                  <Button
                    key="delete"
                    type="link"
                    size="small"
                    icon={<DeleteOutlined />}
                    danger
                    onClick={() => handlePreferenceDelete(item.id)}
                  >
                    Delete
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={`${item.key} (${item.scope === 'global' ? 'Global' : 'Company'})`}
                  description={
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {typeof item.value === 'object' && item.value !== null
                        ? JSON.stringify(item.value, null, 2)
                        : String(item.value ?? '')}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Space>
      </Modal>
    </>
  );
};

export default AIWidget;

