import { Alert, Form, Input, Modal } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { ReviewReportGenerateInput } from '../types/reviewReport'

interface GenerateValues {
  period_start: string
  period_end: string
}

function toUtc(value: string): string {
  return new Date(value).toISOString()
}

export function ReviewReportGenerateModal({
  open,
  onCancel,
  onGenerate,
}: {
  open: boolean
  onCancel: () => void
  onGenerate: (data: ReviewReportGenerateInput) => Promise<void>
}) {
  const [form] = Form.useForm<GenerateValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setError('')
  }, [form, open])

  const submit = async () => {
    const values = await form.validateFields()
    if (new Date(values.period_end).getTime() <= new Date(values.period_start).getTime()) {
      form.setFields([{ name: 'period_end', errors: ['结束时间必须晚于开始时间'] }])
      return
    }
    setSaving(true)
    setError('')
    try {
      await onGenerate({ period_start: toUtc(values.period_start), period_end: toUtc(values.period_end) })
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason.code === 'no_performance_data' ? '当前周期内没有可用于生成报告的经营数据。' : reason.message)
      else setError('经营分析报告生成失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} title="生成经营分析报告" okText="开始生成" cancelText="取消" confirmLoading={saving} onOk={() => void submit()} onCancel={onCancel} destroyOnHidden>
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Alert type="info" showIcon message="请明确选择统计周期" description="系统只汇总完整落在该周期内的经营数据；没有经营数据时不会调用 AI。" className="form-alert" />
      <Form form={form} layout="vertical">
        <Form.Item label="统计开始时间" name="period_start" rules={[{ required: true, message: '请选择开始时间' }]}><Input type="datetime-local" /></Form.Item>
        <Form.Item label="统计结束时间" name="period_end" rules={[{ required: true, message: '请选择结束时间' }]}><Input type="datetime-local" /></Form.Item>
      </Form>
    </Modal>
  )
}

