import { Descriptions, Drawer, Empty, Space, Tag, Timeline, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getGenerationJob } from '../api/generationJobs'
import { PageError, PageLoading } from './PageState'
import type { GenerationJobDetail } from '../types/generationJob'

const statusLabels = {
  pending: '待运行',
  running: '运行中',
  succeeded: '已成功',
  failed: '失败',
  cancelled: '已取消',
  timeout: '超时',
} as const

const eventLabels = {
  created: '创建',
  started: '开始运行',
  succeeded: '运行成功',
  failed: '运行失败',
  retry_requested: '请求重试',
  cancelled: '取消',
  timeout: '超时',
} as const

const statusColors = { pending: 'default', running: 'processing', succeeded: 'success', failed: 'error', cancelled: 'default', timeout: 'warning' } as const

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

function resultSummary(result: Record<string, unknown> | null): string {
  if (!result) return '暂无生成结果'
  const values = [
    typeof result.asset_type === 'string' ? `类型：${result.asset_type}` : '',
    typeof result.url === 'string' ? `URL：${result.url}` : '',
    typeof result.width === 'number' && typeof result.height === 'number' ? `尺寸：${result.width} × ${result.height}` : '',
    typeof result.duration_sec === 'number' ? `时长：${result.duration_sec} 秒` : '',
  ].filter(Boolean)
  return values.length ? values.join('；') : '生成结果已返回'
}

export function GenerationJobDetailDrawer({
  productId,
  jobId,
  open,
  onClose,
}: {
  productId: number
  jobId: number | null
  open: boolean
  onClose: () => void
}) {
  const [detail, setDetail] = useState<GenerationJobDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || jobId === null) return
    let active = true
    setLoading(true)
    setError('')
    getGenerationJob(productId, jobId)
      .then((value) => { if (active) setDetail(value) })
      .catch((reason) => { if (active) setError(reason instanceof ApiError ? reason.message : '任务详情加载失败') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [jobId, open, productId])

  return (
    <Drawer open={open} onClose={onClose} width={720} title={detail ? `生成任务 #${detail.id}` : '生成任务详情'}>
      {loading ? <PageLoading /> : error ? <PageError message={error} /> : detail ? (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="类型">{detail.job_kind === 'image' ? '图片' : '视频'}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[detail.job_status]}>{statusLabels[detail.job_status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="尝试次数">{detail.attempts} / {detail.max_attempts}</Descriptions.Item>
            <Descriptions.Item label="创意方案 ID">{detail.creative_plan_id}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDate(detail.created_at)}</Descriptions.Item>
            <Descriptions.Item label="开始时间">{formatDate(detail.started_at)}</Descriptions.Item>
            <Descriptions.Item label="完成时间">{formatDate(detail.finished_at)}</Descriptions.Item>
            <Descriptions.Item label="执行者">{detail.locked_by || '—'}</Descriptions.Item>
            {detail.error_message && <Descriptions.Item label="错误" span={2}><Typography.Text type="danger">{detail.error_message}</Typography.Text></Descriptions.Item>}
          </Descriptions>
          <div>
            <Typography.Title level={5}>生成结果</Typography.Title>
            <Typography.Paragraph>{resultSummary(detail.result_json)}</Typography.Paragraph>
            {detail.job_status === 'succeeded' && <Typography.Text type="secondary">生成任务成功，结果仍需同步到素材库并经过人工审核。</Typography.Text>}
          </div>
          <div>
            <Typography.Title level={5}>事件时间线</Typography.Title>
            {detail.events.length ? (
              <Timeline items={detail.events.map((event) => ({
                color: event.event_type === 'failed' || event.event_type === 'timeout' ? 'red' : event.event_type === 'succeeded' ? 'green' : 'blue',
                children: <Space direction="vertical" size={0}><Typography.Text strong>{eventLabels[event.event_type] || event.event_type}</Typography.Text><Typography.Text>{event.event_message}</Typography.Text><Typography.Text type="secondary">{formatDate(event.created_at)}</Typography.Text></Space>,
              }))} />
            ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无事件" />}
          </div>
        </Space>
      ) : null}
    </Drawer>
  )
}
