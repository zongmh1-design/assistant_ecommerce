import { Alert, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { Competitor, CompetitorCreate } from '../types/competitor'

interface CompetitorFormValues {
  name: string
  platform: CompetitorCreate['platform']
  url: string
  price?: string
  sales_hint?: string
  title?: string
  main_image?: string
  selling_points_text?: string
  review_keywords_text?: string
}

const platformOptions = [
  { value: 'taobao', label: '淘宝' },
  { value: 'tmall', label: '天猫' },
  { value: 'jd', label: '京东' },
  { value: 'douyin', label: '抖音' },
  { value: 'pinduoduo', label: '拼多多' },
  { value: 'other', label: '其他' },
]
const moneyPattern = /^\d{1,10}(\.\d{1,2})?$/
const lines = (value?: string) => (value || '').split('\n').map((item) => item.trim()).filter(Boolean)

export function CompetitorFormModal({
  open,
  competitor,
  onCancel,
  onSubmit,
}: {
  open: boolean
  competitor: Competitor | null
  onCancel: () => void
  onSubmit: (data: CompetitorCreate) => Promise<void>
}) {
  const [form] = Form.useForm<CompetitorFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setError('')
    if (competitor) {
      form.setFieldsValue({
        name: competitor.name,
        platform: competitor.platform,
        url: competitor.url,
        price: competitor.price || undefined,
        sales_hint: competitor.sales_hint || undefined,
        title: competitor.title || undefined,
        main_image: competitor.main_image || undefined,
        selling_points_text: competitor.selling_points.join('\n'),
        review_keywords_text: competitor.review_keywords.join('\n'),
      })
    }
  }, [open, competitor, form])

  const submit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    setError('')
    try {
      await onSubmit({
        name: values.name.trim(),
        platform: values.platform,
        url: values.url.trim(),
        price: values.price || null,
        sales_hint: values.sales_hint?.trim() || null,
        title: values.title?.trim() || null,
        main_image: values.main_image?.trim() || null,
        selling_points: lines(values.selling_points_text),
        review_keywords: lines(values.review_keywords_text),
      })
    } catch (reason) {
      if (reason instanceof ApiError) {
        setError(reason.message)
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({
          name: name as keyof CompetitorFormValues,
          errors: [message],
        }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('竞品保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={competitor ? '编辑竞品' : '手工添加竞品'}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      onOk={submit}
      onCancel={onCancel}
      width={680}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form<CompetitorFormValues> form={form} layout="vertical" initialValues={{ platform: 'other' }}>
        <div className="form-grid">
          <Form.Item label="竞品名称" name="name" rules={[{ required: true, message: '请输入竞品名称' }]}>
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item label="平台" name="platform" rules={[{ required: true, message: '请选择平台' }]}>
            <Select options={platformOptions} />
          </Form.Item>
          <Form.Item label="公开商品链接" name="url" rules={[{ required: true, message: '请输入公开商品链接' }, { type: 'url', message: '请输入有效 URL' }]}>
            <Input maxLength={2048} />
          </Form.Item>
          <Form.Item label="价格" name="price" rules={[{ pattern: moneyPattern, message: '请输入最多两位小数的非负金额' }]}>
            <Input inputMode="decimal" />
          </Form.Item>
          <Form.Item label="标题快照" name="title">
            <Input maxLength={300} />
          </Form.Item>
          <Form.Item label="销量提示" name="sales_hint">
            <Input maxLength={200} />
          </Form.Item>
        </div>
        <Form.Item label="主图 URL" name="main_image" rules={[{ type: 'url', message: '请输入有效 URL' }]}>
          <Input maxLength={2048} />
        </Form.Item>
        <Form.Item label="卖点（每行一个）" name="selling_points_text">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="评价关键词（每行一个）" name="review_keywords_text">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
