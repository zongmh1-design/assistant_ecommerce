import { Alert, Form, Input, InputNumber, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { AdExperiment } from '../types/adExperiment'
import type { CreativePlan } from '../types/creativePlan'
import type { GeneratedAsset } from '../types/asset'
import type { PerformanceRecord, PerformanceRecordCreate, PerformanceRecordUpdate } from '../types/performanceRecord'
import type { PromotionLink } from '../types/promotionLink'

interface PerformanceFormValues {
  period_start: string
  period_end: string
  impressions: number | null
  clicks: number | null
  conversions: number | null
  spend: string
  revenue: string
  notes?: string
  creative_plan_id?: number
  generated_asset_id?: number
  promotion_link_id?: number
  experiment_id?: number
}

function toLocalInput(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function toUtc(value: string): string {
  return new Date(value).toISOString()
}

function fromRecord(record: PerformanceRecord): PerformanceFormValues {
  return {
    period_start: toLocalInput(record.period_start),
    period_end: toLocalInput(record.period_end),
    impressions: record.impressions,
    clicks: record.clicks,
    conversions: record.conversions,
    spend: record.spend,
    revenue: record.revenue,
    notes: record.notes ?? undefined,
    creative_plan_id: record.creative_plan_id ?? undefined,
    generated_asset_id: record.generated_asset_id ?? undefined,
    promotion_link_id: record.promotion_link_id ?? undefined,
    experiment_id: record.experiment_id ?? undefined,
  }
}

function basePayload(values: PerformanceFormValues): PerformanceRecordCreate {
  return {
    period_start: toUtc(values.period_start),
    period_end: toUtc(values.period_end),
    impressions: Number(values.impressions),
    clicks: Number(values.clicks),
    conversions: Number(values.conversions),
    spend: values.spend.trim(),
    revenue: values.revenue.trim(),
    notes: values.notes?.trim() || null,
    ...(values.creative_plan_id ? { creative_plan_id: values.creative_plan_id } : {}),
    ...(values.generated_asset_id ? { generated_asset_id: values.generated_asset_id } : {}),
    ...(values.promotion_link_id ? { promotion_link_id: values.promotion_link_id } : {}),
    ...(values.experiment_id ? { experiment_id: values.experiment_id } : {}),
  }
}

function changedFields(values: PerformanceFormValues, initial: PerformanceFormValues): PerformanceRecordUpdate {
  const changes: PerformanceRecordUpdate = {}
  const contentFields: Array<keyof Pick<PerformanceFormValues, 'period_start' | 'period_end' | 'impressions' | 'clicks' | 'conversions' | 'spend' | 'revenue'>> = [
    'period_start', 'period_end', 'impressions', 'clicks', 'conversions', 'spend', 'revenue',
  ]
  for (const field of contentFields) {
    if (values[field] !== initial[field]) {
      const value = values[field]
      if (field === 'period_start' || field === 'period_end') changes[field] = toUtc(String(value))
      else if (field === 'spend' || field === 'revenue') changes[field] = String(value).trim()
      else changes[field] = Number(value)
    }
  }
  if ((values.notes ?? '') !== (initial.notes ?? '')) changes.notes = values.notes?.trim() || null
  const relations: Array<keyof Pick<PerformanceFormValues, 'creative_plan_id' | 'generated_asset_id' | 'promotion_link_id' | 'experiment_id'>> = [
    'creative_plan_id', 'generated_asset_id', 'promotion_link_id', 'experiment_id',
  ]
  for (const field of relations) {
    if (values[field] !== initial[field]) changes[field] = values[field] ?? null
  }
  return changes
}

export function PerformanceRecordFormModal({
  open,
  record,
  creativePlans,
  assets,
  links,
  experiments,
  onCancel,
  onCreate,
  onUpdate,
}: {
  open: boolean
  record: PerformanceRecord | null
  creativePlans: CreativePlan[]
  assets: GeneratedAsset[]
  links: PromotionLink[]
  experiments: AdExperiment[]
  onCancel: () => void
  onCreate: (data: PerformanceRecordCreate) => Promise<void>
  onUpdate: (data: PerformanceRecordUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<PerformanceFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setError('')
    if (record) form.setFieldsValue(fromRecord(record))
    else form.setFieldsValue({ spend: '0.00', revenue: '0.00' })
  }, [form, open, record])

  const submit = async () => {
    const values = await form.validateFields()
    if (new Date(values.period_end).getTime() <= new Date(values.period_start).getTime()) {
      form.setFields([{ name: 'period_end', errors: ['结束时间必须晚于开始时间'] }])
      return
    }
    setSaving(true)
    setError('')
    try {
      if (record) {
        const initial = fromRecord(record)
        const changes = changedFields(values, initial)
        if (!Object.keys(changes).length) {
          onCancel()
          return
        }
        await onUpdate(changes)
      } else {
        await onCreate(basePayload(values))
      }
    } catch (reason) {
      if (reason instanceof ApiError) {
        setError(reason.message)
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({ name: name as keyof PerformanceFormValues, errors: [message] }))
        if (fields.length) form.setFields(fields)
      } else setError(record ? '经营数据保存失败，请稍后重试' : '经营数据创建失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={record ? '编辑经营数据' : '录入经营数据'}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      width={780}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form form={form} layout="vertical">
        <div className="form-grid">
          <Form.Item label="统计开始时间" name="period_start" rules={[{ required: true, message: '请选择开始时间' }]}>
            <Input type="datetime-local" />
          </Form.Item>
          <Form.Item label="统计结束时间" name="period_end" rules={[{ required: true, message: '请选择结束时间' }]}>
            <Input type="datetime-local" />
          </Form.Item>
          <Form.Item label="曝光" name="impressions" rules={[{ required: true, message: '请输入曝光数' }, { type: 'number', min: 0, message: '曝光必须是非负整数' }]}>
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="点击" name="clicks" rules={[{ required: true, message: '请输入点击数' }, { type: 'number', min: 0, message: '点击必须是非负整数' }, ({ getFieldValue }) => ({ validator(_, value) { if (value === null || value === undefined || value <= getFieldValue('impressions')) return Promise.resolve(); return Promise.reject(new Error('点击不能超过曝光')) } })]}>
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="转化" name="conversions" rules={[{ required: true, message: '请输入转化数' }, { type: 'number', min: 0, message: '转化必须是非负整数' }, ({ getFieldValue }) => ({ validator(_, value) { if (value === null || value === undefined || value <= getFieldValue('clicks')) return Promise.resolve(); return Promise.reject(new Error('转化不能超过点击')) } })]}>
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="支出" name="spend" rules={[{ required: true, message: '请输入支出金额' }, { pattern: /^\d+(\.\d{1,2})?$/, message: '请输入最多两位小数的非负金额' }]}>
            <Input prefix="¥" />
          </Form.Item>
          <Form.Item label="收入" name="revenue" rules={[{ required: true, message: '请输入收入金额' }, { pattern: /^\d+(\.\d{1,2})?$/, message: '请输入最多两位小数的非负金额' }]}>
            <Input prefix="¥" />
          </Form.Item>
        </div>
        <Form.Item label="关联实验（仅 running / finished）" name="experiment_id">
          <Select allowClear placeholder="可选" options={experiments.map((item) => ({ value: item.id, label: `${item.experiment_name} · ${item.experiment_status}` }))} />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="关联创意方案" name="creative_plan_id"><Select allowClear placeholder="可选" options={creativePlans.map((item) => ({ value: item.id, label: `${item.title} · ${item.plan_type}` }))} /></Form.Item>
          <Form.Item label="关联审核素材" name="generated_asset_id"><Select allowClear placeholder="可选" options={assets.map((item) => ({ value: item.id, label: `${item.asset_type} v${item.version_no}` }))} /></Form.Item>
          <Form.Item label="关联推广链接" name="promotion_link_id"><Select allowClear placeholder="可选" options={links.map((item) => ({ value: item.id, label: item.link_name }))} /></Form.Item>
        </div>
        <Form.Item label="备注" name="notes"><Input.TextArea rows={3} /></Form.Item>
        <TypographyNote />
      </Form>
    </Modal>
  )
}

function TypographyNote() {
  return <div style={{ color: '#6b7280', fontSize: 12 }}>CTR、CVR、ROI 由后端根据原始经营数据计算，不能在此表单中填写。</div>
}
