import { EditOutlined, PlusOutlined, ReloadOutlined, RobotOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Descriptions, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import {
  createPromotionLink,
  generatePromotionSuggestion,
  getPromotionLink,
  listPromotionLinks,
  updatePromotionLink,
} from '../api/promotionLinks'
import { useAuth } from '../auth/AuthContext'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import { PromotionLinkDetailDrawer } from '../components/PromotionLinkDetailDrawer'
import { PromotionLinkFormModal } from '../components/PromotionLinkFormModal'
import type {
  PromotionLink,
  PromotionLinkCreate,
  PromotionLinkStatus,
  PromotionLinkSuggestion,
  PromotionLinkUpdate,
} from '../types/promotionLink'

const PAGE_SIZE = 20

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

function utmSummary(link: PromotionLink): string {
  return Object.entries(link.utm_json)
    .filter(([, value]) => value)
    .map(([key, value]) => `${utmLabels[key] || key}：${value}`)
    .join('；') || '未设置 UTM'
}

export function PromotionLinksPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<PromotionLink[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<PromotionLinkStatus | undefined>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [suggestion, setSuggestion] = useState<PromotionLinkSuggestion | null>(null)
  const [suggestionLoading, setSuggestionLoading] = useState(false)
  const [suggestionError, setSuggestionError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<PromotionLink | null>(null)
  const [formSuggestion, setFormSuggestion] = useState<PromotionLinkSuggestion | null>(null)
  const [detailLink, setDetailLink] = useState<PromotionLink | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listPromotionLinks(productId, {
        page,
        page_size: PAGE_SIZE,
        ...(statusFilter ? { status: statusFilter } : {}),
      })
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '推广链接列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, productId, statusFilter])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [statusFilter])

  const handleGenerateSuggestion = async () => {
    setSuggestionLoading(true)
    setSuggestionError('')
    try {
      const result = await generatePromotionSuggestion(productId)
      setSuggestion(result)
      message.success('推广参数建议已生成')
    } catch (reason) {
      const safeMessage = reason instanceof ApiError ? reason.message : '推广建议生成失败，请稍后重试'
      setSuggestionError(safeMessage)
      message.error(safeMessage)
    } finally {
      setSuggestionLoading(false)
    }
  }

  const openCreate = (fromSuggestion: PromotionLinkSuggestion | null = null) => {
    setEditing(null)
    setFormSuggestion(fromSuggestion)
    setFormOpen(true)
  }

  const openDetail = (link: PromotionLink) => {
    setDetailLink(link)
    setDetailOpen(true)
  }

  const handleFormSubmit = async (data: PromotionLinkCreate | PromotionLinkUpdate) => {
    if (editing) {
      const updated = await updatePromotionLink(productId, editing.id, data as PromotionLinkUpdate)
      const refreshed = await getPromotionLink(productId, editing.id)
      const finalValue = refreshed || updated
      setItems((current) => current.map((item) => item.id === finalValue.id ? finalValue : item))
      setDetailLink((current) => current?.id === finalValue.id ? finalValue : current)
      message.success('推广链接已保存')
    } else {
      const created = await createPromotionLink(productId, data as PromotionLinkCreate)
      message.success(`推广链接已创建，tracking code：${created.tracking_code}`)
      await load()
    }
    setFormOpen(false)
    setEditing(null)
    setFormSuggestion(null)
  }

  const columns: ColumnsType<PromotionLink> = [
    {
      title: '链接名称',
      dataIndex: 'link_name',
      render: (value: string, link) => <Button type="link" onClick={() => openDetail(link)}>{value}</Button>,
    },
    { title: '场景', dataIndex: 'scene_text', render: (value: string | null) => value || '—' },
    { title: '状态', dataIndex: 'status', render: (value: PromotionLinkStatus) => <Tag color={statusColors[value]}>{statusLabels[value]}</Tag> },
    { title: 'tracking code', dataIndex: 'tracking_code', render: (value: string) => <Typography.Text code>{value}</Typography.Text> },
    {
      title: '跳转地址',
      dataIndex: 'target_url',
      render: (value: string) => <Typography.Text ellipsis={{ tooltip: value }} style={{ maxWidth: 220, display: 'inline-block' }}>{value}</Typography.Text>,
    },
    { title: '累计点击', dataIndex: 'click_count' },
    { title: 'UTM', key: 'utm', render: (_, link) => <Typography.Text type="secondary" ellipsis={{ tooltip: utmSummary(link) }} style={{ maxWidth: 230, display: 'inline-block' }}>{utmSummary(link)}</Typography.Text> },
    { title: '创建时间', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
    {
      title: '操作',
      key: 'actions',
      render: (_, link) => (
        <Space>
          <Button type="link" onClick={() => openDetail(link)}>查看详情</Button>
          {canWrite && <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(link); setFormSuggestion(null); setFormOpen(true) }}>编辑</Button>}
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>推广链接</Typography.Title>
          <Typography.Text type="secondary">AI 只提供推广参数建议；正式跳转地址和 tracking code 由业务流程控制。</Typography.Text>
        </div>
        {canWrite && (
          <Space>
            <Button icon={<RobotOutlined />} loading={suggestionLoading} disabled={suggestionLoading} onClick={() => void handleGenerateSuggestion()}>生成推广建议</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => openCreate()}>创建推广链接</Button>
          </Space>
        )}
      </div>
      {canWrite && <Alert type="info" showIcon title="推广链接边界" description="建议生成后仍需人工填写 target URL 并创建正式链接；测试跳转会真实记录一次点击。" />}
      {suggestionError && <Alert type="error" showIcon closable title="推广建议生成失败" description={suggestionError} onClose={() => setSuggestionError('')} />}
      {suggestion && (
        <Card
          className="promotion-suggestion-card"
          title="AI 推广参数建议（仅建议，尚未创建正式链接）"
          extra={canWrite && <Button type="primary" onClick={() => openCreate(suggestion)}>使用此建议创建链接</Button>}
        >
          <DescriptionsLikeSuggestion suggestion={suggestion} />
        </Card>
      )}
      <Card title="推广链接列表" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            aria-label="链接状态"
            allowClear
            placeholder="全部状态"
            style={{ width: 150 }}
            value={statusFilter}
            onChange={(value: PromotionLinkStatus | undefined) => setStatusFilter(value)}
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
          />
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
          <PageEmpty description="当前商品暂无推广链接" />
        ) : (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Table<PromotionLink> rowKey="id" columns={columns} dataSource={items} pagination={false} scroll={{ x: 1100 }} />
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </Space>
        )}
      </Card>
      <PromotionLinkFormModal
        open={formOpen}
        link={editing}
        suggestion={formSuggestion}
        onCancel={() => { setFormOpen(false); setEditing(null); setFormSuggestion(null) }}
        onSubmit={handleFormSubmit}
      />
      <PromotionLinkDetailDrawer
        productId={productId}
        link={detailLink}
        open={detailOpen}
        canWrite={canWrite}
        onClose={() => setDetailOpen(false)}
        onEdit={(link) => { setDetailOpen(false); setEditing(link); setFormSuggestion(null); setFormOpen(true) }}
      />
    </Space>
  )
}

function DescriptionsLikeSuggestion({ suggestion }: { suggestion: PromotionLinkSuggestion }) {
  return (
    <Descriptions bordered column={2} size="small">
      <Descriptions.Item label="建议名称">{suggestion.link_name}</Descriptions.Item>
      <Descriptions.Item label="建议场景">{suggestion.scene_text}</Descriptions.Item>
      <Descriptions.Item label="UTM 来源">{suggestion.utm_source}</Descriptions.Item>
      <Descriptions.Item label="UTM 媒介">{suggestion.utm_medium}</Descriptions.Item>
      <Descriptions.Item label="UTM 活动">{suggestion.utm_campaign}</Descriptions.Item>
      <Descriptions.Item label="UTM 内容">{suggestion.utm_content}</Descriptions.Item>
      <Descriptions.Item label="建议理由" span={2}>{suggestion.rationale}</Descriptions.Item>
    </Descriptions>
  )
}
