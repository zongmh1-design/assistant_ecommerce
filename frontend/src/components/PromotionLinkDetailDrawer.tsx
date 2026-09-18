import { CopyOutlined, ExportOutlined, ReloadOutlined } from '@ant-design/icons'
import { App, Button, Card, Descriptions, Drawer, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { buildTrackingUrl, getPromotionLink, listPromotionLinkClicks } from '../api/promotionLinks'
import { PageEmpty, PageError, PageLoading } from './PageState'
import { PaginationControls } from './PaginationControls'
import type { PromotionLink, PromotionLinkClick, PromotionLinkStatus } from '../types/promotionLink'

const PAGE_SIZE = 10

const statusLabels: Record<PromotionLinkStatus, string> = { active: '启用', inactive: '已停用' }
const statusColors: Record<PromotionLinkStatus, string> = { active: 'green', inactive: 'default' }
const utmLabels: Record<string, string> = {
  utm_source: '来源',
  utm_medium: '媒介',
  utm_campaign: '活动',
  utm_content: '内容',
  utm_term: '关键词',
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function utmText(link: PromotionLink): string {
  return Object.entries(link.utm_json)
    .filter(([, value]) => value)
    .map(([key, value]) => `${utmLabels[key] || key}：${value}`)
    .join('；') || '未设置 UTM'
}

async function copyText(value: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
      return true
    }
    const input = document.createElement('textarea')
    input.value = value
    input.setAttribute('readonly', '')
    input.style.position = 'fixed'
    input.style.opacity = '0'
    document.body.appendChild(input)
    input.select()
    const copied = document.execCommand('copy')
    document.body.removeChild(input)
    return copied
  } catch {
    return false
  }
}

export function PromotionLinkDetailDrawer({
  productId,
  link,
  open,
  canWrite,
  onClose,
  onEdit,
}: {
  productId: number
  link: PromotionLink | null
  open: boolean
  canWrite: boolean
  onClose: () => void
  onEdit?: (link: PromotionLink) => void
}) {
  const { message } = App.useApp()
  const [detail, setDetail] = useState<PromotionLink | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [clicks, setClicks] = useState<PromotionLinkClick[]>([])
  const [clickTotal, setClickTotal] = useState(0)
  const [clickPage, setClickPage] = useState(1)
  const [clickLoading, setClickLoading] = useState(false)
  const [clickError, setClickError] = useState('')
  const [clickReloadKey, setClickReloadKey] = useState(0)

  useEffect(() => {
    if (!open || !link) return
    setDetail(null)
    setDetailError('')
    setDetailLoading(true)
    getPromotionLink(productId, link.id)
      .then(setDetail)
      .catch((reason) => setDetailError(reason instanceof ApiError ? reason.message : '推广链接详情加载失败'))
      .finally(() => setDetailLoading(false))
  }, [link, open, productId])

  useEffect(() => {
    if (!open || !link) return
    setClickPage(1)
  }, [link, open])

  useEffect(() => {
    if (!open || !link) return
    setClickLoading(true)
    setClickError('')
    listPromotionLinkClicks(productId, link.id, { page: clickPage, page_size: PAGE_SIZE })
      .then((response) => {
        setClicks(response.items)
        setClickTotal(response.total)
      })
      .catch((reason) => setClickError(reason instanceof ApiError ? reason.message : '点击记录加载失败'))
      .finally(() => setClickLoading(false))
  }, [clickPage, clickReloadKey, link, open, productId])

  const activeLink = detail || link
  const trackingUrl = activeLink ? buildTrackingUrl(activeLink.tracking_code) : ''

  const handleCopy = async (value: string, label: string) => {
    const copied = await copyText(value)
    if (copied) message.success(`${label}已复制`)
    else message.error('复制失败，请手动选择并复制')
  }

  const handleRedirect = () => {
    if (!activeLink || activeLink.status !== 'active') return
    message.info('测试跳转会记录一次点击')
    window.open(buildTrackingUrl(activeLink.tracking_code), '_blank')
  }

  const clickColumns: ColumnsType<PromotionLinkClick> = [
    { title: '点击时间', dataIndex: 'clicked_at', render: (value: string) => formatDate(value) },
    { title: '客户端 IP', dataIndex: 'client_ip', render: (value: string | null) => value || '未记录' },
    { title: 'User-Agent', dataIndex: 'user_agent', render: (value: string | null) => value || '未记录' },
  ]

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={760}
      title={activeLink ? `推广链接详情 · ${activeLink.link_name}` : '推广链接详情'}
    >
      {detailLoading ? <PageLoading /> : detailError ? <PageError message={detailError} /> : activeLink ? (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="链接名称">{activeLink.link_name}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[activeLink.status]}>{statusLabels[activeLink.status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="跳转地址" span={2}><a href={activeLink.target_url} target="_blank" rel="noreferrer">{activeLink.target_url}</a></Descriptions.Item>
            <Descriptions.Item label="tracking code"><Typography.Text copyable>{activeLink.tracking_code}</Typography.Text></Descriptions.Item>
            <Descriptions.Item label="累计点击">{activeLink.click_count}</Descriptions.Item>
            <Descriptions.Item label="使用场景" span={2}>{activeLink.scene_text || '—'}</Descriptions.Item>
            <Descriptions.Item label="UTM 参数" span={2}>{utmText(activeLink)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDate(activeLink.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatDate(activeLink.updated_at)}</Descriptions.Item>
          </Descriptions>
          <Card size="small" title="公开 tracking 跳转入口">
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Typography.Text copyable={{ text: trackingUrl }}>{trackingUrl}</Typography.Text>
              <Space wrap>
                <Button icon={<CopyOutlined />} onClick={() => void handleCopy(activeLink.tracking_code, 'tracking code')}>复制 tracking code</Button>
                <Button icon={<CopyOutlined />} onClick={() => void handleCopy(trackingUrl, 'tracking URL')}>复制完整 tracking URL</Button>
                <Button
                  type="primary"
                  icon={<ExportOutlined />}
                  disabled={activeLink.status !== 'active'}
                  onClick={handleRedirect}
                >
                  测试跳转
                </Button>
              </Space>
              <Typography.Text type="secondary">
                {activeLink.status === 'active' ? '测试跳转会记录一次点击。' : '链接已停用，不能继续跳转。'}
              </Typography.Text>
            </Space>
          </Card>
          <Card
            size="small"
            title="点击记录"
            extra={<Button size="small" icon={<ReloadOutlined />} loading={clickLoading} onClick={() => setClickReloadKey((current) => current + 1)}>刷新</Button>}
          >
            {clickLoading ? <PageLoading /> : clickError ? <PageError message={clickError} onRetry={() => setClickReloadKey((current) => current + 1)} /> : clicks.length === 0 ? (
              <PageEmpty description="暂无点击记录" />
            ) : (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Table<PromotionLinkClick> rowKey="id" columns={clickColumns} dataSource={clicks} pagination={false} scroll={{ x: 620 }} />
                <PaginationControls page={clickPage} pageSize={PAGE_SIZE} total={clickTotal} onChange={setClickPage} />
              </Space>
            )}
          </Card>
          {canWrite && onEdit && <Button onClick={() => onEdit(activeLink)}>编辑推广链接</Button>}
        </Space>
      ) : null}
    </Drawer>
  )
}
