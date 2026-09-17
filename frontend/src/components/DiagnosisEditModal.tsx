import { Alert, Form, Input, Modal } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { ProductDiagnosis, ProductDiagnosisUpdate } from '../types/diagnosis'

interface DiagnosisFormValues {
  positioning: string
  price_band: string
  audience_insights: string
  pain_points: string
  selling_point_analysis: string
  risks: string
  recommendations: string
}

const arrayFields: Array<keyof Pick<DiagnosisFormValues, 'audience_insights' | 'pain_points' | 'selling_point_analysis' | 'risks' | 'recommendations'>> = [
  'audience_insights',
  'pain_points',
  'selling_point_analysis',
  'risks',
  'recommendations',
]

function toLines(value: string): string[] {
  return value.split('\n').map((item) => item.trim()).filter(Boolean)
}

function toFormValues(diagnosis: ProductDiagnosis): DiagnosisFormValues {
  return {
    positioning: diagnosis.positioning,
    price_band: diagnosis.price_band,
    audience_insights: diagnosis.audience_insights.join('\n'),
    pain_points: diagnosis.pain_points.join('\n'),
    selling_point_analysis: diagnosis.selling_point_analysis.join('\n'),
    risks: diagnosis.risks.join('\n'),
    recommendations: diagnosis.recommendations.join('\n'),
  }
}

function toUpdate(values: DiagnosisFormValues, initial: DiagnosisFormValues): ProductDiagnosisUpdate {
  const changes: ProductDiagnosisUpdate = {}
  if (values.positioning !== initial.positioning) changes.positioning = values.positioning.trim()
  if (values.price_band !== initial.price_band) changes.price_band = values.price_band.trim()
  for (const field of arrayFields) {
    if (values[field] !== initial[field]) changes[field] = toLines(values[field])
  }
  return changes
}

export function DiagnosisEditModal({
  open,
  diagnosis,
  onCancel,
  onSubmit,
}: {
  open: boolean
  diagnosis: ProductDiagnosis | null
  onCancel: () => void
  onSubmit: (data: ProductDiagnosisUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<DiagnosisFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !diagnosis) return
    form.setFieldsValue(toFormValues(diagnosis))
    setError('')
  }, [open, diagnosis, form])

  const submit = async () => {
    const values = await form.validateFields()
    const initial = diagnosis ? toFormValues(diagnosis) : values
    const changes = toUpdate(values, initial)
    if (!Object.keys(changes).length) {
      onCancel()
      return
    }
    setSaving(true)
    setError('')
    try {
      await onSubmit(changes)
    } catch (reason) {
      if (reason instanceof ApiError) {
        setError(reason.message)
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({
          name: name as keyof DiagnosisFormValues,
          errors: [message],
        }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('诊断保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title="编辑商品诊断"
      okText="保存修改"
      cancelText="取消"
      confirmLoading={saving}
      onOk={submit}
      onCancel={onCancel}
      width={760}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form form={form} layout="vertical">
        <Form.Item label="商品定位" name="positioning" rules={[{ required: true, message: '请输入商品定位' }]}>
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item label="价格带分析" name="price_band" rules={[{ required: true, message: '请输入价格带分析' }]}>
          <Input.TextArea rows={2} />
        </Form.Item>
        <Form.Item label="目标人群洞察（每行一项）" name="audience_insights" rules={[{ required: true, message: '请输入目标人群洞察' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="用户痛点（每行一项）" name="pain_points" rules={[{ required: true, message: '请输入用户痛点' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="卖点分析（每行一项）" name="selling_point_analysis" rules={[{ required: true, message: '请输入卖点分析' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="风险（每行一项）" name="risks" rules={[{ required: true, message: '请输入风险' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="优化建议（每行一项）" name="recommendations" rules={[{ required: true, message: '请输入优化建议' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
