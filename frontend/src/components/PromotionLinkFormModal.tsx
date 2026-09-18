import { Alert, Form, Input, Modal, Select } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type {
  PromotionLink,
  PromotionLinkCreate,
  PromotionLinkStatus,
  PromotionLinkSuggestion,
  PromotionLinkUtm,
  PromotionLinkUpdate,
} from '../types/promotionLink'

type UtmField = 'utm_source' | 'utm_medium' | 'utm_campaign' | 'utm_content' | 'utm_term'

interface PromotionLinkFormValues {
  link_name: string
  target_url?: string
  scene_text?: string
  status?: PromotionLinkStatus
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  utm_content?: string
  utm_term?: string
}

const utmFields: Array<{ name: UtmField; label: string }> = [
  { name: 'utm_source', label: 'UTM 来源（utm_source）' },
  { name: 'utm_medium', label: 'UTM 媒介（utm_medium）' },
  { name: 'utm_campaign', label: 'UTM 活动（utm_campaign）' },
  { name: 'utm_content', label: 'UTM 内容（utm_content）' },
  { name: 'utm_term', label: 'UTM 关键词（utm_term）' },
]

const statusOptions = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' },
]

function cleanUtm(values: PromotionLinkFormValues): PromotionLinkUtm {
  const utm: PromotionLinkUtm = {}
  for (const { name } of utmFields) {
    const value = values[name]?.trim()
    if (value) utm[name] = value
  }
  return utm
}

function normalizedText(value?: string | null): string {
  return value?.trim() || ''
}

function valuesFromLink(link: PromotionLink): PromotionLinkFormValues {
  return {
    link_name: link.link_name,
    target_url: link.target_url,
    scene_text: link.scene_text || undefined,
    status: link.status,
    ...Object.fromEntries(utmFields.map(({ name }) => [name, link.utm_json[name] || undefined])),
  }
}

function valuesFromSuggestion(suggestion: PromotionLinkSuggestion): PromotionLinkFormValues {
  return {
    link_name: suggestion.link_name,
    scene_text: suggestion.scene_text,
    target_url: undefined,
    utm_source: suggestion.utm_source,
    utm_medium: suggestion.utm_medium,
    utm_campaign: suggestion.utm_campaign,
    utm_content: suggestion.utm_content,
    utm_term: undefined,
    status: 'active',
  }
}

function updateFromValues(values: PromotionLinkFormValues, link: PromotionLink): PromotionLinkUpdate {
  const initial = valuesFromLink(link)
  const changes: PromotionLinkUpdate = {}
  const linkName = values.link_name.trim()
  const targetUrl = (values.target_url || '').trim()
  const sceneText = normalizedText(values.scene_text)
  if (linkName !== initial.link_name) changes.link_name = linkName
  if (targetUrl !== initial.target_url) changes.target_url = targetUrl
  if (sceneText !== normalizedText(initial.scene_text)) changes.scene_text = sceneText || null
  if (values.status !== initial.status && values.status) changes.status = values.status

  const currentUtm = cleanUtm(values)
  const initialUtm = cleanUtm(initial)
  if (JSON.stringify(currentUtm) !== JSON.stringify(initialUtm)) changes.utm_json = currentUtm
  return changes
}

export function PromotionLinkFormModal({
  open,
  link,
  suggestion,
  onCancel,
  onSubmit,
}: {
  open: boolean
  link: PromotionLink | null
  suggestion?: PromotionLinkSuggestion | null
  onCancel: () => void
  onSubmit: (data: PromotionLinkCreate | PromotionLinkUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<PromotionLinkFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setError('')
    if (link) form.setFieldsValue(valuesFromLink(link))
    else if (suggestion) form.setFieldsValue(valuesFromSuggestion(suggestion))
    else form.setFieldsValue({ status: 'active' })
  }, [form, link, open, suggestion])

  const submit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    setError('')
    try {
      if (link) {
        const changes = updateFromValues(values, link)
        if (!Object.keys(changes).length) {
          onCancel()
          return
        }
        await onSubmit(changes)
      } else {
        await onSubmit({
          link_name: values.link_name.trim(),
          target_url: (values.target_url || '').trim(),
          scene_text: normalizedText(values.scene_text) || null,
          utm_json: cleanUtm(values),
        })
      }
    } catch (reason) {
      if (reason instanceof ApiError) {
        setError(reason.message)
        const fields = Object.entries(reason.fieldErrors)
          .filter(([name]) => name !== 'utm_json')
          .map(([name, message]) => ({ name: name as keyof PromotionLinkFormValues, errors: [message] }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('推广链接保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={link ? '编辑推广链接' : '创建正式推广链接'}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      width={720}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      {!link && suggestion && (
        <Alert
          type="info"
          showIcon
          title="正在使用 AI 建议预填"
          description="AI 建议不会生成 tracking code，也不会决定跳转地址；请由你明确填写 target URL。"
          className="form-alert"
        />
      )}
      <Form<PromotionLinkFormValues> form={form} layout="vertical">
        <Form.Item label="链接名称" name="link_name" rules={[{ required: true, message: '请输入链接名称' }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item
          label="跳转地址（target URL）"
          name="target_url"
          rules={[
            { required: true, message: '请输入跳转地址' },
            {
              validator: (_, value: string | undefined) => {
                if (!value) return Promise.resolve()
                try {
                  const url = new URL(value.trim())
                  if (url.protocol === 'http:' || url.protocol === 'https:') return Promise.resolve()
                } catch {
                  // 统一返回安全、可理解的表单错误，不展示解析异常。
                }
                return Promise.reject(new Error('跳转地址必须是 http 或 https URL'))
              },
            },
          ]}
        >
          <Input placeholder="https://example.com/product" maxLength={2048} />
        </Form.Item>
        <Form.Item label="使用场景" name="scene_text">
          <Input maxLength={300} placeholder="例如：社交媒体、短视频简介" />
        </Form.Item>
        {link && (
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择链接状态' }]}>
            <Select options={statusOptions} />
          </Form.Item>
        )}
        <div className="utm-grid">
          {utmFields.map(({ name, label }) => (
            <Form.Item key={name} label={label} name={name}>
              <Input maxLength={200} />
            </Form.Item>
          ))}
        </div>
      </Form>
    </Modal>
  )
}
