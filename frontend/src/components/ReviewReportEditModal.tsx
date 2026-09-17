import { Alert, Button, Form, Input, Modal, Select, Space } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type { ProblemJudgement, ReviewInsight, ReviewNextAction, ReviewReport, ReviewReportUpdate } from '../types/reviewReport'

interface ReviewFormValues {
  summary_text: string
  insights_json: ReviewInsight[]
  problem_judgements_json: ProblemJudgement[]
  next_actions_json: ReviewNextAction[]
}

function valuesFromReport(report: ReviewReport): ReviewFormValues {
  return {
    summary_text: report.summary_text,
    insights_json: report.insights_json,
    problem_judgements_json: report.problem_judgements_json,
    next_actions_json: report.next_actions_json,
  }
}

function toChanges(values: ReviewFormValues, initial: ReviewFormValues): ReviewReportUpdate {
  const changes: ReviewReportUpdate = {}
  if (values.summary_text !== initial.summary_text) changes.summary_text = values.summary_text.trim()
  if (JSON.stringify(values.insights_json) !== JSON.stringify(initial.insights_json)) changes.insights_json = values.insights_json
  if (JSON.stringify(values.problem_judgements_json) !== JSON.stringify(initial.problem_judgements_json)) changes.problem_judgements_json = values.problem_judgements_json
  if (JSON.stringify(values.next_actions_json) !== JSON.stringify(initial.next_actions_json)) changes.next_actions_json = values.next_actions_json
  return changes
}

export function ReviewReportEditModal({
  open,
  report,
  onCancel,
  onSubmit,
}: {
  open: boolean
  report: ReviewReport | null
  onCancel: () => void
  onSubmit: (data: ReviewReportUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<ReviewFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !report) return
    form.setFieldsValue(valuesFromReport(report))
    setError('')
  }, [form, open, report])

  const submit = async () => {
    const values = await form.validateFields()
    const initial = report ? valuesFromReport(report) : values
    const changes = toChanges(values, initial)
    if (!Object.keys(changes).length) {
      onCancel()
      return
    }
    setSaving(true)
    setError('')
    try {
      await onSubmit(changes)
    } catch (reason) {
      if (reason instanceof ApiError) setError(reason.message)
      else setError('报告保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title="编辑经营分析报告"
      width={900}
      okText="保存修改"
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form form={form} layout="vertical">
        <Form.Item label="周期摘要" name="summary_text" rules={[{ required: true, message: '请输入周期摘要' }]}><Input.TextArea rows={3} /></Form.Item>
        <Form.List name="insights_json">
          {(fields, { add, remove }) => (
            <section className="review-edit-section">
              <Space style={{ justifyContent: 'space-between', width: '100%' }}><strong>核心发现</strong><Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ title: '', finding: '', evidence: '' })}>添加发现</Button></Space>
              {fields.map(({ key, name, ...restField }) => (
                <div className="review-edit-row" key={key}>
                  <Form.Item {...restField} label="标题" name={[name, 'title']} rules={[{ required: true, message: '请输入标题' }]}><Input /></Form.Item>
                  <Form.Item {...restField} label="发现" name={[name, 'finding']} rules={[{ required: true, message: '请输入发现' }]}><Input.TextArea rows={2} /></Form.Item>
                  <Form.Item {...restField} label="数据依据" name={[name, 'evidence']} rules={[{ required: true, message: '请输入数据依据' }]}><Input.TextArea rows={2} /></Form.Item>
                  <Button danger type="link" onClick={() => remove(name)}>删除</Button>
                </div>
              ))}
            </section>
          )}
        </Form.List>
        <Form.List name="problem_judgements_json">
          {(fields, { add, remove }) => (
            <section className="review-edit-section">
              <Space style={{ justifyContent: 'space-between', width: '100%' }}><strong>问题判断</strong><Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ problem: '', evidence: '', severity: 'medium' })}>添加问题</Button></Space>
              {fields.map(({ key, name, ...restField }) => (
                <div className="review-edit-row" key={key}>
                  <Form.Item {...restField} label="问题" name={[name, 'problem']} rules={[{ required: true, message: '请输入问题' }]}><Input.TextArea rows={2} /></Form.Item>
                  <Form.Item {...restField} label="数据依据" name={[name, 'evidence']} rules={[{ required: true, message: '请输入数据依据' }]}><Input.TextArea rows={2} /></Form.Item>
                  <Form.Item {...restField} label="严重程度" name={[name, 'severity']} rules={[{ required: true }]}><Select options={[{ value: 'low', label: '低' }, { value: 'medium', label: '中' }, { value: 'high', label: '高' }]} /></Form.Item>
                  <Button danger type="link" onClick={() => remove(name)}>删除</Button>
                </div>
              ))}
            </section>
          )}
        </Form.List>
        <Form.List name="next_actions_json">
          {(fields, { add, remove }) => (
            <section className="review-edit-section">
              <Space style={{ justifyContent: 'space-between', width: '100%' }}><strong>下一步动作</strong><Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ action: '', rationale: '', priority: 'medium' })}>添加动作</Button></Space>
              {fields.map(({ key, name, ...restField }) => (
                <div className="review-edit-row" key={key}>
                  <Form.Item {...restField} label="动作" name={[name, 'action']} rules={[{ required: true, message: '请输入动作' }]}><Input.TextArea rows={2} /></Form.Item>
                  <Form.Item {...restField} label="理由" name={[name, 'rationale']} rules={[{ required: true, message: '请输入理由' }]}><Input.TextArea rows={2} /></Form.Item>
                  <Form.Item {...restField} label="优先级" name={[name, 'priority']} rules={[{ required: true }]}><Select options={[{ value: 'low', label: '低' }, { value: 'medium', label: '中' }, { value: 'high', label: '高' }]} /></Form.Item>
                  <Button danger type="link" onClick={() => remove(name)}>删除</Button>
                </div>
              ))}
            </section>
          )}
        </Form.List>
      </Form>
    </Modal>
  )
}

