import { Alert, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { Store, StoreCreate } from '../types/store'

const platformOptions = [
  { value: 'taobao', label: '淘宝' },
  { value: 'tmall', label: '天猫' },
  { value: 'jd', label: '京东' },
  { value: 'douyin', label: '抖音' },
  { value: 'pinduoduo', label: '拼多多' },
  { value: 'other', label: '其他' },
]

export function StoreFormModal({
  open,
  store,
  onCancel,
  onSubmit,
}: {
  open: boolean
  store: Store | null
  onCancel: () => void
  onSubmit: (data: StoreCreate) => Promise<void>
}) {
  const [form] = Form.useForm<StoreCreate>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setError('')
    form.setFieldsValue(
      store
        ? {
            store_name: store.store_name,
            platform: store.platform,
            external_store_id: store.external_store_id,
            owner_name: store.owner_name,
            remark: store.remark,
          }
        : { platform: 'taobao' },
    )
    if (!store) form.resetFields(['store_name', 'external_store_id', 'owner_name', 'remark'])
  }, [open, store, form])

  const submit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    setError('')
    try {
      await onSubmit({
        ...values,
        external_store_id: values.external_store_id || null,
        owner_name: values.owner_name || null,
        remark: values.remark || null,
      })
    } catch (reason) {
      if (reason instanceof ApiError) {
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({
          name: name as keyof StoreCreate,
          errors: [message],
        }))
        if (fields.length) form.setFields(fields)
        setError(reason.message)
      } else {
        setError('保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={store ? '编辑店铺' : '创建店铺'}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      onOk={submit}
      onCancel={onCancel}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon message={error} className="form-alert" />}
      <Form form={form} layout="vertical">
        <Form.Item label="店铺名称" name="store_name" rules={[{ required: true, message: '请输入店铺名称' }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item label="平台" name="platform" rules={[{ required: true, message: '请选择平台' }]}>
          <Select options={platformOptions} />
        </Form.Item>
        <Form.Item label="平台店铺 ID" name="external_store_id">
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item label="负责人" name="owner_name">
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item label="备注" name="remark">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
