import { Alert, Descriptions, Form, Input, InputNumber, Modal, Select, Space, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { AssetReviewStatus, GeneratedAsset, GeneratedAssetUpdate } from '../types/asset'

interface AssetFormValues {
  review_status: AssetReviewStatus
  usage_scene?: string
  score?: number
  tags_json: string[]
  remark?: string
}

const reviewLabels: Record<AssetReviewStatus, string> = { pending: '待审核', approved: '已通过', rejected: '已驳回' }

function valuesFromAsset(asset: GeneratedAsset): AssetFormValues {
  return {
    review_status: asset.review_status,
    usage_scene: asset.usage_scene || undefined,
    score: asset.score ?? undefined,
    tags_json: [...asset.tags_json],
    remark: asset.remark || undefined,
  }
}

function updateFromValues(values: AssetFormValues, asset: GeneratedAsset): GeneratedAssetUpdate {
  const initial = valuesFromAsset(asset)
  const changes: GeneratedAssetUpdate = {}
  if (values.review_status !== initial.review_status) changes.review_status = values.review_status
  if ((values.usage_scene || '') !== (initial.usage_scene || '')) changes.usage_scene = values.usage_scene?.trim() || null
  if ((values.score ?? null) !== (initial.score ?? null)) changes.score = values.score ?? null
  const tags = [...new Set(values.tags_json.map((tag) => tag.trim()).filter(Boolean))]
  if (JSON.stringify(tags) !== JSON.stringify(initial.tags_json)) changes.tags_json = tags
  if ((values.remark || '') !== (initial.remark || '')) changes.remark = values.remark?.trim() || null
  return changes
}

export function AssetReviewModal({
  open,
  asset,
  canWrite,
  onCancel,
  onSubmit,
}: {
  open: boolean
  asset: GeneratedAsset | null
  canWrite: boolean
  onCancel: () => void
  onSubmit: (data: GeneratedAssetUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<AssetFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !asset) return
    form.resetFields()
    form.setFieldsValue(valuesFromAsset(asset))
    setError('')
  }, [asset, form, open])

  const submit = async () => {
    if (!asset) return
    const values = await form.validateFields()
    const changes = updateFromValues(values, asset)
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
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({ name: name as keyof AssetFormValues, errors: [message] }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('素材信息保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={asset ? `素材 #${asset.id} · ${asset.asset_type === 'image' ? '图片' : '视频'}` : '素材详情'}
      okText="保存修改"
      cancelText="关闭"
      confirmLoading={saving}
      onOk={canWrite ? () => void submit() : undefined}
      onCancel={onCancel}
      footer={canWrite ? undefined : null}
      width={760}
      destroyOnHidden
    >
      {asset && (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="类型">{asset.asset_type === 'image' ? '图片' : '视频'}</Descriptions.Item>
            <Descriptions.Item label="版本">v{asset.version_no}</Descriptions.Item>
            <Descriptions.Item label="模型">{asset.model_name}</Descriptions.Item>
            <Descriptions.Item label="来源任务">#{asset.generation_job_id}</Descriptions.Item>
            <Descriptions.Item label="地址" span={2}><Typography.Text copyable>{asset.asset_url}</Typography.Text></Descriptions.Item>
            {asset.asset_type === 'image' && <Descriptions.Item label="尺寸" span={2}>{asset.width && asset.height ? `${asset.width} × ${asset.height}` : '—'}</Descriptions.Item>}
            {asset.asset_type === 'video' && <Descriptions.Item label="时长" span={2}>{asset.duration_sec !== null ? `${asset.duration_sec} 秒` : '—'}</Descriptions.Item>}
          </Descriptions>
          {!canWrite && <Alert type="info" showIcon title={`审核状态：${reviewLabels[asset.review_status]}`} description="查看人员只能查看素材，不能修改审核和元数据。" />}
          <Form<AssetFormValues> form={form} layout="vertical" disabled={!canWrite}>
            <Form.Item label="审核状态" name="review_status" rules={[{ required: true, message: '请选择审核状态' }]}>
              <Select options={Object.entries(reviewLabels).map(([value, label]) => ({ value, label }))} />
            </Form.Item>
            <Form.Item label="使用场景" name="usage_scene"><Input maxLength={200} placeholder="例如：首页主图" /></Form.Item>
            <Form.Item label="评分（0-100）" name="score" rules={[{ type: 'number', min: 0, max: 100, message: '评分范围为 0-100' }]}>
              <InputNumber min={0} max={100} precision={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="标签" name="tags_json"><Select mode="tags" tokenSeparators={[',']} placeholder="输入后回车添加标签" /></Form.Item>
            <Form.Item label="备注" name="remark"><Input.TextArea rows={3} maxLength={500} /></Form.Item>
          </Form>
        </Space>
      )}
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
    </Modal>
  )
}
