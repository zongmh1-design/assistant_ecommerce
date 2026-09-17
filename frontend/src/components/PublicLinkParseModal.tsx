import { Alert, Button, Descriptions, Form, Input, Modal, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import {
  confirmLinkParseTask,
  createLinkParseTask,
  getLinkParseTask,
  runLinkParseTask,
} from '../api/competitors'
import { ApiError } from '../api/client'
import type { PublicLinkParseTask } from '../types/competitor'

const statusLabels = { pending: '待解析', running: '解析中', succeeded: '解析成功', failed: '解析失败' }
const statusColors = { pending: 'default', running: 'processing', succeeded: 'success', failed: 'error' }

export function PublicLinkParseModal({
  productId,
  open,
  onCancel,
  onConfirmed,
}: {
  productId: number
  open: boolean
  onCancel: () => void
  onConfirmed: () => Promise<void>
}) {
  const [form] = Form.useForm<{ source_url: string }>()
  const [task, setTask] = useState<PublicLinkParseTask | null>(null)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    form.resetFields()
    setTask(null)
    setError('')
  }, [open, form])

  const execute = async (action: () => Promise<PublicLinkParseTask>) => {
    setWorking(true)
    setError('')
    try {
      setTask(await action())
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '解析任务操作失败')
    } finally {
      setWorking(false)
    }
  }

  const createTask = async () => {
    const { source_url } = await form.validateFields()
    await execute(() => createLinkParseTask(productId, source_url.trim()))
  }

  const confirm = async () => {
    if (!task) return
    setWorking(true)
    setError('')
    try {
      await confirmLinkParseTask(productId, task.id)
      await onConfirmed()
      onCancel()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '确认竞品失败')
    } finally {
      setWorking(false)
    }
  }

  const candidate = task?.result_json
  return (
    <Modal open={open} title="从公开链接解析竞品" footer={null} onCancel={onCancel} width={720} destroyOnHidden>
      <Alert
        type="info"
        showIcon
        title="当前后端使用 Mock PublicLinkParser"
        description="浏览器不会抓取第三方页面。解析结果必须由你确认后，才会创建正式竞品。"
        className="form-alert"
      />
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      {!task ? (
        <Form form={form} layout="vertical">
          <Form.Item label="公开商品 URL" name="source_url" rules={[{ required: true, message: '请输入 URL' }, { type: 'url', message: '请输入有效 URL' }]}>
            <Input placeholder="https://example.com/product" />
          </Form.Item>
          <Button type="primary" loading={working} onClick={createTask}>创建解析任务</Button>
        </Form>
      ) : (
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[task.task_status]}>{statusLabels[task.task_status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="尝试次数">{task.attempts}</Descriptions.Item>
            <Descriptions.Item label="来源 URL">{task.source_url}</Descriptions.Item>
          </Descriptions>
          {task.error_message && <Alert type="error" showIcon title="解析失败" description={task.error_message} />}
          {candidate && (
            <div>
              <Typography.Title level={5}>候选竞品数据</Typography.Title>
              <Descriptions bordered column={2}>
                <Descriptions.Item label="名称">{candidate.name || '—'}</Descriptions.Item>
                <Descriptions.Item label="平台">{candidate.platform || '—'}</Descriptions.Item>
                <Descriptions.Item label="价格">{candidate.price ? `¥${candidate.price}` : '—'}</Descriptions.Item>
                <Descriptions.Item label="数据来源">{candidate.data_source || '—'}</Descriptions.Item>
                <Descriptions.Item label="标题" span={2}>{candidate.title || '—'}</Descriptions.Item>
                <Descriptions.Item label="卖点" span={2}>{candidate.selling_points?.join('；') || '—'}</Descriptions.Item>
                <Descriptions.Item label="评价关键词" span={2}>{candidate.review_keywords?.join('；') || '—'}</Descriptions.Item>
              </Descriptions>
            </div>
          )}
          <Space>
            {task.task_status === 'pending' && <Button type="primary" loading={working} onClick={() => void execute(() => runLinkParseTask(productId, task.id))}>开始解析</Button>}
            {task.task_status === 'failed' && <Button type="primary" loading={working} onClick={() => void execute(() => runLinkParseTask(productId, task.id))}>重新解析</Button>}
            {task.task_status === 'running' && <Button loading={working} onClick={() => void execute(() => getLinkParseTask(productId, task.id))}>刷新状态</Button>}
            {task.task_status === 'succeeded' && !task.confirmed_competitor_id && <Button type="primary" loading={working} onClick={confirm}>确认并创建竞品</Button>}
            <Button onClick={onCancel}>关闭</Button>
          </Space>
        </Space>
      )}
    </Modal>
  )
}
