import { Alert, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { GeneratedAsset } from '../types/asset'
import type { AdExperiment, AdExperimentGenerateInput, AdExperimentUpdate } from '../types/adExperiment'
import type { AdRecommendation } from '../types/adRecommendation'
import type { PromotionLink } from '../types/promotionLink'

interface ExperimentFormValues {
  recommendation_id?: number
  related_asset_id?: number
  related_link_id?: number
  experiment_name: string
  target_text: string
  audience_text: string
  budget_amount: string
  success_metric_text: string
  hypothesis_text: string
}

function valuesFromExperiment(experiment: AdExperiment): ExperimentFormValues {
  return {
    recommendation_id: experiment.ad_recommendation_id,
    related_asset_id: experiment.related_asset_id ?? undefined,
    related_link_id: experiment.related_link_id ?? undefined,
    experiment_name: experiment.experiment_name,
    target_text: experiment.target_text,
    audience_text: experiment.audience_text,
    budget_amount: experiment.budget_amount,
    success_metric_text: experiment.success_metric_text,
    hypothesis_text: experiment.hypothesis_text,
  }
}

export function AdExperimentFormModal({
  open,
  experiment,
  recommendationId,
  recommendations,
  assets,
  links,
  onCancel,
  onGenerate,
  onUpdate,
}: {
  open: boolean
  experiment: AdExperiment | null
  recommendationId?: number | null
  recommendations: AdRecommendation[]
  assets: GeneratedAsset[]
  links: PromotionLink[]
  onCancel: () => void
  onGenerate: (data: AdExperimentGenerateInput) => Promise<void>
  onUpdate: (data: AdExperimentUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<ExperimentFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setError('')
    if (experiment) form.setFieldsValue(valuesFromExperiment(experiment))
    else form.setFieldsValue({ recommendation_id: recommendationId ?? undefined })
  }, [experiment, form, open, recommendationId])

  const submit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    setError('')
    try {
      if (experiment) {
        const initial = valuesFromExperiment(experiment)
        const changes: AdExperimentUpdate = {}
        const contentFields: Array<keyof Pick<ExperimentFormValues, 'experiment_name' | 'target_text' | 'audience_text' | 'budget_amount' | 'success_metric_text' | 'hypothesis_text'>> = [
          'experiment_name', 'target_text', 'audience_text', 'budget_amount', 'success_metric_text', 'hypothesis_text',
        ]
        for (const field of contentFields) {
          if (values[field] !== initial[field]) changes[field] = values[field].trim()
        }
        if (values.related_asset_id !== initial.related_asset_id) changes.related_asset_id = values.related_asset_id ?? null
        if (values.related_link_id !== initial.related_link_id) changes.related_link_id = values.related_link_id ?? null
        if (!Object.keys(changes).length) {
          onCancel()
          return
        }
        await onUpdate(changes)
      } else {
        if (values.recommendation_id === undefined) return
        await onGenerate({
          recommendation_id: values.recommendation_id,
          ...(values.related_asset_id !== undefined ? { related_asset_id: values.related_asset_id } : {}),
          ...(values.related_link_id !== undefined ? { related_link_id: values.related_link_id } : {}),
        })
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '实验计划保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={experiment ? '编辑实验计划' : '生成实验计划'}
      okText={experiment ? '保存修改' : '生成实验计划'}
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      width={720}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      {!experiment && <Alert type="info" showIcon title="实验计划边界" description="实验只记录人工规划和执行状态，不会调用广告平台；必须明确选择已确认的投放建议。" className="form-alert" />}
      <Form<ExperimentFormValues> form={form} layout="vertical">
        <Form.Item label="已确认投放建议" name="recommendation_id" rules={[{ required: true, message: '请选择已确认的投放建议' }]}>
          <Select
            disabled={Boolean(experiment)}
            placeholder="请选择已确认的投放建议"
            options={recommendations.map((recommendation) => ({
              value: recommendation.id,
              label: `#${recommendation.id} · ${new Date(recommendation.created_at).toLocaleString('zh-CN')} · ${recommendation.summary_text.slice(0, 36)}`,
            }))}
          />
        </Form.Item>
        <Form.Item label="绑定审核通过素材（可选）" name="related_asset_id">
          <Select
            allowClear
            placeholder="不绑定素材"
            options={assets.map((asset) => ({
              value: asset.id,
              label: `${asset.asset_type === 'image' ? '图片' : '视频'} v${asset.version_no}${asset.usage_scene ? ` · ${asset.usage_scene}` : ''}${asset.score === null ? '' : ` · ${asset.score}分`}`,
            }))}
          />
        </Form.Item>
        <Form.Item label="绑定启用推广链接（可选）" name="related_link_id">
          <Select
            allowClear
            placeholder="不绑定推广链接"
            options={links.map((link) => ({ value: link.id, label: `${link.link_name}${link.scene_text ? ` · ${link.scene_text}` : ''} · 点击 ${link.click_count}` }))}
          />
        </Form.Item>
        {experiment && (
          <>
            <Form.Item label="实验名称" name="experiment_name" rules={[{ required: true, message: '请输入实验名称' }]}><Input maxLength={200} /></Form.Item>
            <Form.Item label="实验目标" name="target_text" rules={[{ required: true, message: '请输入实验目标' }]}><Input.TextArea rows={2} /></Form.Item>
            <Form.Item label="目标人群" name="audience_text" rules={[{ required: true, message: '请输入目标人群' }]}><Input.TextArea rows={2} /></Form.Item>
            <Form.Item label="预算金额" name="budget_amount" rules={[{ required: true, message: '请输入预算金额' }]}><Input placeholder="例如 100.00" /></Form.Item>
            <Form.Item label="成功指标" name="success_metric_text" rules={[{ required: true, message: '请输入成功指标' }]}><Input.TextArea rows={2} /></Form.Item>
            <Form.Item label="实验假设" name="hypothesis_text" rules={[{ required: true, message: '请输入实验假设' }]}><Input.TextArea rows={3} /></Form.Item>
          </>
        )}
      </Form>
    </Modal>
  )
}
