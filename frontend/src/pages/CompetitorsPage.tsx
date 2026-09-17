import { EditOutlined, LinkOutlined, PlusOutlined } from '@ant-design/icons'
import { App, Button, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { createCompetitor, listCompetitors, updateCompetitor } from '../api/competitors'
import { useAuth } from '../auth/AuthContext'
import { CompetitorFormModal } from '../components/CompetitorFormModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import { PublicLinkParseModal } from '../components/PublicLinkParseModal'
import type { Competitor, CompetitorCreate } from '../types/competitor'

const PAGE_SIZE = 20

export function CompetitorsPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<Competitor[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [parseOpen, setParseOpen] = useState(false)
  const [editing, setEditing] = useState<Competitor | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listCompetitors(productId, { page, page_size: PAGE_SIZE })
      setItems(result.items)
      setTotal(result.total)
    } catch (reason) {
      const message = reason instanceof ApiError && reason.status === 404
        ? '当前商品下不存在该竞品或商品不存在'
        : reason instanceof ApiError ? reason.message : '竞品列表加载失败'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [productId, page])

  useEffect(() => {
    void load()
  }, [load])

  const columns: ColumnsType<Competitor> = [
    { title: '竞品名称', dataIndex: 'name' },
    { title: '平台', dataIndex: 'platform', render: (value: string) => <Tag>{value}</Tag> },
    { title: '标题快照', dataIndex: 'title', render: (value: string | null) => value || '—' },
    { title: '价格', dataIndex: 'price', render: (value: string | null) => value ? `¥${value}` : '—' },
    { title: '销量提示', dataIndex: 'sales_hint', render: (value: string | null) => value || '—' },
    { title: '公开链接', dataIndex: 'url', render: (value: string) => <a href={value} target="_blank" rel="noreferrer">查看链接</a> },
    { title: '更新时间', dataIndex: 'updated_at', render: (value: string) => new Date(value).toLocaleString('zh-CN') },
  ]
  if (canWrite) {
    columns.push({
      title: '操作',
      key: 'actions',
      render: (_, item) => <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(item); setFormOpen(true) }}>编辑</Button>,
    })
  }

  return (
    <>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>竞品</Typography.Title>
          <Typography.Text type="secondary">手工维护竞品，或通过后端 Mock Parser 解析公开链接后人工确认。</Typography.Text>
        </div>
        {canWrite && (
          <Space>
            <Button icon={<LinkOutlined />} onClick={() => setParseOpen(true)}>从公开链接解析</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setFormOpen(true) }}>手工添加</Button>
          </Space>
        )}
      </div>
      {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
        <PageEmpty description="暂无竞品" />
      ) : (
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <Table rowKey="id" columns={columns} dataSource={items} pagination={false} />
          <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </Space>
      )}
      <CompetitorFormModal
        open={formOpen}
        competitor={editing}
        onCancel={() => setFormOpen(false)}
        onSubmit={async (data: CompetitorCreate) => {
          if (editing) await updateCompetitor(editing.id, data)
          else await createCompetitor(productId, data)
          setFormOpen(false)
          message.success(editing ? '竞品已更新' : '竞品已添加')
          await load()
        }}
      />
      <PublicLinkParseModal
        productId={productId}
        open={parseOpen}
        onCancel={() => setParseOpen(false)}
        onConfirmed={async () => {
          message.success('候选数据已确认并创建为正式竞品')
          await load()
        }}
      />
    </>
  )
}
