import { Alert, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { ProductSku, ProductSkuCreate } from '../types/sku'

interface SkuFormValues {
  sku_code: string
  sku_name: string
  spec_text?: string
  price: string
  cost?: string
  status: ProductSkuCreate['status']
  platform_sku_id?: string
}

const moneyPattern = /^\d{1,10}(\.\d{1,2})?$/

function parseSpecs(value?: string): Record<string, string> {
  const result: Record<string, string> = {}
  for (const line of (value || '').split('\n').map((item) => item.trim()).filter(Boolean)) {
    const separator = line.indexOf('=')
    if (separator <= 0 || !line.slice(separator + 1).trim()) {
      throw new Error('规格请按“名称=值”格式填写，每行一个')
    }
    result[line.slice(0, separator).trim()] = line.slice(separator + 1).trim()
  }
  return result
}

export function SkuFormModal({
  open,
  sku,
  onCancel,
  onSubmit,
}: {
  open: boolean
  sku: ProductSku | null
  onCancel: () => void
  onSubmit: (data: ProductSkuCreate) => Promise<void>
}) {
  const [form] = Form.useForm<SkuFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setError('')
    if (sku) {
      form.setFieldsValue({
        sku_code: sku.sku_code,
        sku_name: sku.sku_name,
        spec_text: Object.entries(sku.spec_json).map(([key, value]) => `${key}=${value}`).join('\n'),
        price: sku.price,
        cost: sku.cost || undefined,
        status: sku.status,
        platform_sku_id: sku.platform_sku_id || undefined,
      })
    }
  }, [open, sku, form])

  const submit = async () => {
    const values = await form.validateFields()
    let specJson: Record<string, string>
    try {
      specJson = parseSpecs(values.spec_text)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : '规格格式错误'
      form.setFields([{ name: 'spec_text', errors: [message] }])
      return
    }
    setSaving(true)
    setError('')
    try {
      await onSubmit({
        sku_code: values.sku_code.trim(),
        sku_name: values.sku_name.trim(),
        spec_json: specJson,
        price: values.price,
        cost: values.cost || null,
        status: values.status,
        platform_sku_id: values.platform_sku_id?.trim() || null,
      })
    } catch (reason) {
      if (reason instanceof ApiError) {
        setError(reason.message)
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({
          name: name as keyof SkuFormValues,
          errors: [message],
        }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('SKU 保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={sku ? '编辑 SKU' : '创建 SKU'}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      onOk={submit}
      onCancel={onCancel}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form<SkuFormValues> form={form} layout="vertical" initialValues={{ status: 'active' }}>
        <Form.Item label="SKU 编码" name="sku_code" rules={[{ required: true, message: '请输入 SKU 编码' }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item label="SKU 名称" name="sku_name" rules={[{ required: true, message: '请输入 SKU 名称' }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item label="规格（每行 名称=值）" name="spec_text">
          <Input.TextArea rows={3} placeholder={'颜色=黑色\n容量=10000mAh'} />
        </Form.Item>
        <Form.Item
          label="价格"
          name="price"
          rules={[{ required: true, message: '请输入价格' }, { pattern: moneyPattern, message: '请输入最多两位小数的非负金额' }]}
        >
          <Input inputMode="decimal" />
        </Form.Item>
        <Form.Item label="成本" name="cost" rules={[{ pattern: moneyPattern, message: '请输入最多两位小数的非负金额' }]}>
          <Input inputMode="decimal" />
        </Form.Item>
        <Form.Item label="状态" name="status" rules={[{ required: true }]}>
          <Select options={[{ value: 'active', label: '启用' }, { value: 'inactive', label: '停用' }]} />
        </Form.Item>
        <Form.Item label="平台 SKU ID" name="platform_sku_id">
          <Input maxLength={100} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
