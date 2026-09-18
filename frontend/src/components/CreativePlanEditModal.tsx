import { Alert, Button, Form, Input, Modal, Space } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type {
  CreativePlan,
  CreativePlanUpdate,
  MainImageContent,
  StoryboardScene,
  VideoScriptContent,
} from '../types/creativePlan'

interface CreativePlanFormValues {
  title: string
  rationale_text: string
  visual_structure?: string
  core_copy?: string
  highlighted_selling_points?: string
  opening_hook?: string
  voiceover?: string
  conversion_cta?: string
  storyboard?: StoryboardScene[]
}

function isMainImageContent(value: unknown): value is MainImageContent {
  if (typeof value !== 'object' || value === null) return false
  const content = value as Record<string, unknown>
  return ['visual_structure', 'core_copy', 'highlighted_selling_points'].every((key) => Array.isArray(content[key]))
}

function isVideoScriptContent(value: unknown): value is VideoScriptContent {
  if (typeof value !== 'object' || value === null) return false
  const content = value as Record<string, unknown>
  return typeof content.opening_hook === 'string'
    && Array.isArray(content.storyboard)
    && Array.isArray(content.voiceover)
    && typeof content.conversion_cta === 'string'
}

function linesToArray(value: string | undefined): string[] {
  return (value || '').split('\n').map((item) => item.trim()).filter(Boolean)
}

function arrayToLines(value: string[]): string {
  return value.join('\n')
}

function valuesFromPlan(plan: CreativePlan): CreativePlanFormValues {
  const values: CreativePlanFormValues = {
    title: plan.title,
    rationale_text: plan.rationale_text,
  }
  if (plan.plan_type === 'main_image' && isMainImageContent(plan.content_json)) {
    values.visual_structure = arrayToLines(plan.content_json.visual_structure)
    values.core_copy = arrayToLines(plan.content_json.core_copy)
    values.highlighted_selling_points = arrayToLines(plan.content_json.highlighted_selling_points)
  }
  if (plan.plan_type === 'video_script' && isVideoScriptContent(plan.content_json)) {
    values.opening_hook = plan.content_json.opening_hook
    values.voiceover = arrayToLines(plan.content_json.voiceover)
    values.conversion_cta = plan.content_json.conversion_cta
    values.storyboard = plan.content_json.storyboard.map((scene) => ({ ...scene }))
  }
  return values
}

function updateFromValues(values: CreativePlanFormValues, plan: CreativePlan): CreativePlanUpdate {
  const initial = valuesFromPlan(plan)
  const changes: CreativePlanUpdate = {}
  if (values.title !== initial.title) changes.title = values.title.trim()
  if (values.rationale_text !== initial.rationale_text) changes.rationale_text = values.rationale_text.trim()

  if (plan.plan_type === 'main_image') {
    const initialContent = isMainImageContent(plan.content_json) ? plan.content_json : {
      visual_structure: [],
      core_copy: [],
      highlighted_selling_points: [],
    }
    const currentContent: MainImageContent = {
      visual_structure: linesToArray(values.visual_structure),
      core_copy: linesToArray(values.core_copy),
      highlighted_selling_points: linesToArray(values.highlighted_selling_points),
    }
    if (JSON.stringify(currentContent) !== JSON.stringify(initialContent)) changes.content_json = currentContent
  } else {
    const initialContent = isVideoScriptContent(plan.content_json) ? plan.content_json : {
      opening_hook: '',
      storyboard: [],
      voiceover: [],
      conversion_cta: '',
    }
    const currentContent: VideoScriptContent = {
      opening_hook: (values.opening_hook || '').trim(),
      storyboard: (values.storyboard || []).map((scene, index) => ({
        scene_no: Number(scene.scene_no) || index + 1,
        visual: scene.visual.trim(),
        duration_hint: scene.duration_hint.trim(),
        voiceover: scene.voiceover.trim(),
      })),
      voiceover: linesToArray(values.voiceover),
      conversion_cta: (values.conversion_cta || '').trim(),
    }
    if (JSON.stringify(currentContent) !== JSON.stringify(initialContent)) changes.content_json = currentContent
  }
  return changes
}

export function CreativePlanEditModal({
  open,
  plan,
  onCancel,
  onSubmit,
}: {
  open: boolean
  plan: CreativePlan | null
  onCancel: () => void
  onSubmit: (data: CreativePlanUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<CreativePlanFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !plan) return
    form.resetFields()
    form.setFieldsValue(valuesFromPlan(plan))
    setError('')
  }, [form, open, plan])

  const submit = async () => {
    if (!plan) return
    const values = await form.validateFields()
    const changes = updateFromValues(values, plan)
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
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({ name: name as keyof CreativePlanFormValues, errors: [message] }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('创意方案保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={plan?.plan_type === 'main_image' ? '编辑主图方案' : '编辑视频脚本'}
      okText="保存修改"
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      width={800}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      {plan && (
        <Form<CreativePlanFormValues> form={form} layout="vertical">
          <Form.Item label="方案标题" name="title" rules={[{ required: true, message: '请输入方案标题' }]}>
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item label="方案理由" name="rationale_text" rules={[{ required: true, message: '请输入方案理由' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          {plan.plan_type === 'main_image' ? (
            <>
              <Form.Item label="画面结构（每行一项）" name="visual_structure" rules={[{ required: true, message: '请输入画面结构' }]}>
                <Input.TextArea rows={4} />
              </Form.Item>
              <Form.Item label="核心文案（每行一项）" name="core_copy" rules={[{ required: true, message: '请输入核心文案' }]}>
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item label="重点卖点（每行一项）" name="highlighted_selling_points" rules={[{ required: true, message: '请输入重点卖点' }]}>
                <Input.TextArea rows={3} />
              </Form.Item>
            </>
          ) : (
            <>
              <Form.Item label="开头钩子" name="opening_hook" rules={[{ required: true, message: '请输入开头钩子' }]}>
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.Item label="口播文案（每行一项）" name="voiceover" rules={[{ required: true, message: '请输入口播文案' }]}>
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item label="转化引导" name="conversion_cta" rules={[{ required: true, message: '请输入转化引导' }]}>
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.List name="storyboard">
                {(fields, { add, remove }) => (
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {fields.map((field, index) => (
                      <CardLikeScene key={field.key} fieldName={field.name} index={index} onRemove={() => remove(field.name)} />
                    ))}
                    <ButtonLikeAdd onAdd={() => add({ scene_no: fields.length + 1, visual: '', duration_hint: '', voiceover: '' })} />
                  </Space>
                )}
              </Form.List>
            </>
          )}
        </Form>
      )}
    </Modal>
  )
}

function CardLikeScene({ fieldName, index, onRemove }: { fieldName: number; index: number; onRemove: () => void }) {
  return (
    <div className="storyboard-edit-row">
      <Space align="start" style={{ width: '100%' }}>
        <Form.Item label={`分镜 ${index + 1}`} name={[fieldName, 'scene_no']} rules={[{ required: true }]}>
          <Input type="number" min={1} style={{ width: 90 }} />
        </Form.Item>
        <Form.Item label="画面" name={[fieldName, 'visual']} rules={[{ required: true, message: '请输入画面描述' }]} style={{ flex: 1 }}>
          <Input />
        </Form.Item>
        <Form.Item label="时长提示" name={[fieldName, 'duration_hint']} rules={[{ required: true, message: '请输入时长提示' }]} style={{ width: 150 }}>
          <Input />
        </Form.Item>
        <Form.Item label="分镜口播" name={[fieldName, 'voiceover']} rules={[{ required: true, message: '请输入分镜口播' }]} style={{ flex: 1 }}>
          <Input />
        </Form.Item>
        <ButtonLikeRemove onRemove={onRemove} />
      </Space>
    </div>
  )
}

function ButtonLikeAdd({ onAdd }: { onAdd: () => void }) {
  return <Button onClick={onAdd}>增加分镜</Button>
}

function ButtonLikeRemove({ onRemove }: { onRemove: () => void }) {
  return <Button type="link" danger onClick={onRemove}>删除</Button>
}
