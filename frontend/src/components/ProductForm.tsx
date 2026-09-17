import { Alert, Button, Card, Form, Input, Select, Space } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { listStores } from '../api/stores'
import type { Product, ProductCreate } from '../types/product'
import type { Store } from '../types/store'

interface ProductFormValues {
  store_id: number
  name: string
  platform: ProductCreate['platform']
  category?: string
  price: string
  cost?: string
  target_audience?: string
  selling_points_text?: string
  product_url?: string
  images_text?: string
  status: NonNullable<ProductCreate['status']>
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

function lines(value?: string): string[] {
  return (value || '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function toPayload(values: ProductFormValues): ProductCreate {
  return {
    store_id: values.store_id,
    name: values.name.trim(),
    platform: values.platform,
    category: values.category?.trim() || null,
    price: values.price,
    cost: values.cost || null,
    target_audience: values.target_audience?.trim() || null,
    selling_points: lines(values.selling_points_text),
    product_url: values.product_url?.trim() || null,
    images_json: lines(values.images_text),
    status: values.status,
  }
}

export function ProductForm({
  product,
  submitText,
  onSubmit,
  onCancel,
}: {
  product?: Product
  submitText: string
  onSubmit: (data: ProductCreate) => Promise<void>
  onCancel: () => void
}) {
  const [form] = Form.useForm<ProductFormValues>()
  const [stores, setStores] = useState<Store[]>([])
  const [storesLoading, setStoresLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listStores({ page: 1, page_size: 100 })
      .then((result) => setStores(result.items))
      .catch((reason) => setError(reason instanceof ApiError ? reason.message : '店铺列表加载失败'))
      .finally(() => setStoresLoading(false))
  }, [])

  useEffect(() => {
    if (!product) return
    form.setFieldsValue({
      store_id: product.store_id,
      name: product.name,
      platform: product.platform,
      category: product.category || undefined,
      price: product.price,
      cost: product.cost || undefined,
      target_audience: product.target_audience || undefined,
      selling_points_text: product.selling_points.join('\n'),
      product_url: product.product_url || undefined,
      images_text: product.images_json.join('\n'),
      status: product.status,
    })
  }, [product, form])

  const submit = async (values: ProductFormValues) => {
    setSaving(true)
    setError('')
    try {
      await onSubmit(toPayload(values))
    } catch (reason) {
      if (reason instanceof ApiError) {
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({
          name: name as keyof ProductFormValues,
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
    <Card>
      {error && <Alert type="error" showIcon message={error} className="form-alert" />}
      <Form<ProductFormValues>
        form={form}
        layout="vertical"
        onFinish={submit}
        initialValues={{ platform: 'taobao', status: 'draft', selling_points_text: '', images_text: '' }}
      >
        <div className="form-grid">
          <Form.Item label="所属店铺" name="store_id" rules={[{ required: true, message: '请选择店铺' }]}>
            <Select
              loading={storesLoading}
              options={stores.map((store) => ({ value: store.id, label: store.store_name }))}
              placeholder={stores.length === 0 && !storesLoading ? '请先创建店铺' : '请选择店铺'}
            />
          </Form.Item>
          <Form.Item label="商品名称" name="name" rules={[{ required: true, message: '请输入商品名称' }]}>
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item label="平台" name="platform" rules={[{ required: true, message: '请选择平台' }]}>
            <Select options={platformOptions} />
          </Form.Item>
          <Form.Item label="分类" name="category">
            <Input maxLength={100} />
          </Form.Item>
          <Form.Item
            label="价格"
            name="price"
            rules={[
              { required: true, message: '请输入价格' },
              { pattern: moneyPattern, message: '请输入最多两位小数的非负金额' },
            ]}
          >
            <Input inputMode="decimal" />
          </Form.Item>
          <Form.Item label="成本" name="cost" rules={[{ pattern: moneyPattern, message: '请输入最多两位小数的非负金额' }]}>
            <Input inputMode="decimal" />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'draft', label: '草稿' },
                { value: 'active', label: '启用' },
                { value: 'inactive', label: '停用' },
              ]}
            />
          </Form.Item>
          <Form.Item label="商品链接" name="product_url" rules={[{ type: 'url', message: '请输入有效 URL' }]}>
            <Input maxLength={2048} />
          </Form.Item>
        </div>
        <Form.Item label="目标人群" name="target_audience">
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item label="卖点（每行一个）" name="selling_points_text">
          <Input.TextArea rows={4} />
        </Form.Item>
        <Form.Item label="图片 URL（每行一个）" name="images_text">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={saving}>
            {submitText}
          </Button>
          <Button onClick={onCancel}>取消</Button>
        </Space>
      </Form>
    </Card>
  )
}
