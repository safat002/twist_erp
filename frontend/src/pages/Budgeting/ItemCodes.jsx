import React, { useEffect, useMemo, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, InputNumber, Space, Switch, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../../services/api';
import { useCompany } from '../../contexts/CompanyContext';

const ItemCodes = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [uoms, setUoms] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const { currentCompany } = useCompany();
  const [form] = Form.useForm();
  const [categories, setCategories] = useState([]);
  const [subCategories, setSubCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [codesRes, uomRes, catRes] = await Promise.all([
        api.get('/api/v1/budgets/item-codes/'),
        api.get('/api/v1/budgets/uoms/'),
        api.get('/api/v1/budgets/item-categories/'),
      ]);
      const items = Array.isArray(codesRes.data) ? codesRes.data : codesRes.data?.results || [];
      const uomList = Array.isArray(uomRes.data) ? uomRes.data : uomRes.data?.results || [];
      const cats = Array.isArray(catRes.data) ? catRes.data : catRes.data?.results || [];
      setData(items);
      setUoms(uomList);
      setCategories(cats);
    } catch (e) {
      message.error('Failed to load item codes');
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const columns = useMemo(
    () => [
      { title: 'Code', dataIndex: 'code', key: 'code' },
      { title: 'Name', dataIndex: 'name', key: 'name' },
      { title: 'Category', dataIndex: 'category_name', key: 'category_name' },
      { title: 'Sub-Category', dataIndex: 'sub_category_name', key: 'sub_category_name' },
      { title: 'UoM', dataIndex: 'uom_name', key: 'uom_name' },
      {
        title: 'Standard Price',
        dataIndex: 'standard_price',
        key: 'standard_price',
        render: (v) => Number(v || 0).toFixed(2),
      },
      {
        title: 'Active',
        dataIndex: 'is_active',
        key: 'is_active',
        render: (v) => (v ? 'Yes' : 'No'),
      },
    ],
    [],
  );

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      // Ensure active-company header is aligned with UI selection
      try {
        const activeId = currentCompany?.id;
        if (activeId) {
          const stored = localStorage.getItem('twist-active-company');
          if (!stored || String(stored) !== String(activeId)) {
            localStorage.setItem('twist-active-company', String(activeId));
          }
        }
      } catch (_) {}

      const payload = {
        name: values.name,
        category: values.category_text || '',
        category_id: values.category_id || null,
        sub_category_id: values.sub_category_id || null,
        uom: values.uom,
        standard_price: values.standard_price || 0,
        is_active: values.is_active ?? true,
      };

      const postOnce = async () => api.post('/api/v1/budgets/item-codes/', payload);

      try {
        await postOnce();
      } catch (err) {
        // If backend still lacks active company in session, set and retry once
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail || '';
        if (status === 400 && /Active company is required/i.test(String(detail)) && currentCompany?.id) {
          try {
            await api.post('/api/v1/companies/companies/activate/', { id: currentCompany.id });
            await postOnce();
          } catch (e2) {
            throw e2;
          }
        } else {
          throw err;
        }
      }
      message.success('Item code created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      if (e?.errorFields) return; // form errors
      const similar = e?.response?.data?.similar;
      if (Array.isArray(similar) && similar.length) {
        Modal.confirm({
          title: 'Similar Item Codes exist',
          content: (
            <div>
              <p>We found similar codes in your group. Create anyway?</p>
              <ul>
                {similar.map((s) => (
                  <li key={s.id}>
                    <strong>{s.code}</strong> — {s.name} {s.uom ? `(${s.uom})` : ''}
                  </li>
                ))}
              </ul>
            </div>
          ),
          okText: 'Create Anyway',
          cancelText: 'Cancel',
          onOk: async () => {
            try {
              setSaving(true);
              const v = await form.validateFields();
              const payload2 = {
                name: v.name,
                category: v.category_text || '',
                category_id: v.category_id || null,
                sub_category_id: v.sub_category_id || null,
                uom: v.uom,
                standard_price: v.standard_price || 0,
                is_active: v.is_active ?? true,
              };
              const postForce = async () => api.post('/api/v1/budgets/item-codes/?force=1', payload2);
              try {
                await postForce();
              } catch (err3) {
                const status = err3?.response?.status;
                const detail = err3?.response?.data?.detail || '';
                if (status === 400 && /Active company is required/i.test(String(detail)) && currentCompany?.id) {
                  await api.post('/api/v1/companies/companies/activate/', { id: currentCompany.id });
                  await postForce();
                } else {
                  throw err3;
                }
              }
              message.success('Item code created');
              setOpen(false);
              form.resetFields();
              load();
            } catch (err2) {
              const detail2 = (err2?.response?.data && Array.isArray(err2.response.data.name) && err2.response.data.name[0]) || err2?.response?.data?.detail || 'Could not create item code';
              message.error(detail2);
            } finally {
              setSaving(false);
            }
          },
        });
      } else {
        const detail = (e?.response?.data && Array.isArray(e.response.data.name) && e.response.data.name[0]) || e?.response?.data?.detail || 'Could not create item code';
        message.error(detail);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="Budget Item Codes"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          New Item Code
        </Button>
      }
    >
      <Table columns={columns} dataSource={data} loading={loading} rowKey="id" pagination={{ pageSize: 10 }} />

      <Modal title="Create Item Code" open={open} onCancel={() => setOpen(false)} onOk={handleCreate} confirmLoading={saving} okText="Create">
        <Form layout="vertical" form={form} initialValues={{ is_active: true }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}> 
            <Input />
          </Form.Item>
          <Form.Item name="category_id" label="Category">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={(categories || []).map((c) => ({ value: c.id, label: `${c.code} - ${c.name}` }))}
              onChange={async (val) => {
                setSelectedCategory(val || null);
                form.setFieldsValue({ sub_category_id: null });
                if (val) {
                  try {
                    const { data: sc } = await api.get('/api/v1/budgets/item-sub-categories/', { params: { category: val } });
                    setSubCategories(Array.isArray(sc) ? sc : sc?.results || []);
                  } catch (_) {
                    setSubCategories([]);
                  }
                } else {
                  setSubCategories([]);
                }
              }}
            />
          </Form.Item>
          <Form.Item name="sub_category_id" label="Sub-Category">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              disabled={!selectedCategory}
              options={(subCategories || []).map((s) => ({ value: s.id, label: `${s.code} - ${s.name}` }))}
            />
          </Form.Item>
          <Form.Item name="category_text" label="Category (free text, optional)">
            <Input placeholder="Legacy free-text category (optional)" />
          </Form.Item>
          <Form.Item name="uom" label="Unit of Measure" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(uoms || []).map((u) => ({ value: u.id, label: `${u.short_name || u.code} - ${u.name}` }))}
            />
          </Form.Item>
          <Form.Item name="standard_price" label="Standard Price">
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default ItemCodes;



