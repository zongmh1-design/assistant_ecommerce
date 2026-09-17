import { Alert, Form, Input, Modal } from 'antd'
import { useState } from 'react'
import { ApiError } from '../api/client'
import type { AdRecommendationConfirmation, AdRecommendationConfirmStatus } from '../types/adRecommendation'

export function AdRecommendationConfirmationModal({
  open,
  decision,
  onCancel,
  onSubmit,
}: {
  open: boolean
  decision: Exclude<AdRecommendationConfirmStatus, 'pending'> | null
  onCancel: () => void
  onSubmit: (data: AdRecommendationConfirmation) => Promise<void>
}) {
  const [form] = Form.useForm<{ confirm_remark?: string }>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!decision) return
    const values = await form.validateFields()
    setSaving(true)
    setError('')
    try {
      await onSubmit({ confirm_status: decision, confirm_remark: values.confirm_remark?.trim() || null })
      form.resetFields()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '人工决策保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={decision === 'confirmed' ? '确认投放建议' : '驳回投放建议'}
      okText={decision === 'confirmed' ? '确认建议' : '驳回建议'}
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Alert
        type="info"
        showIcon
        title="人工决策说明"
        description="确认仅代表该建议可以用于后续实验规划，不代表系统已经执行广告投放。"
        className="form-alert"
      />
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form form={form} layout="vertical">
        <Form.Item label="确认备注" name="confirm_remark">
          <Input.TextArea rows={4} placeholder="可选，记录本次人工判断依据" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
