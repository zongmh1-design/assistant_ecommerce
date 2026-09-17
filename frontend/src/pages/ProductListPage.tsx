import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Card, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { listProducts } from '../api/products'
import { useAuth } from '../auth/AuthContext'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type { Product } from '../types/product'

const PAGE_SIZE = 10
const statusLabels = { draft: '草稿', active: '启用', inactive: '停用' }
const statusColors = { draft: 'default', active: 'green', inactive: 'red' }

export function ProductListPage() {
  const { canWrite } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState<Product[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listProducts({ page, page_size: PAGE_SIZE })
      setItems(result.items)
      setTotal(result.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '商品列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    void load()
  }, [load])

  const columns: ColumnsType<Product> = [
    { title: '商品名称', dataIndex: 'name', render: (value: string, item) => <Link to={`/products/${item.id}`}>{value}</Link> },
    { title: '平台', dataIndex: 'platform' },
    { title: '分类', dataIndex: 'category', render: (value: string | null) => value || '—' },
    { title: '价格', dataIndex: 'price', render: (value: string) => `¥${value}` },
    {
      title: '状态',
      dataIndex: 'status',
      render: (value: Product['status']) => <Tag color={statusColors[value]}>{statusLabels[value]}</Tag>,
    },
    { title: '创建时间', dataIndex: 'created_at', render: (value: string) => new Date(value).toLocaleString('zh-CN') },
  ]
  if (canWrite) {
    columns.push({
      title: '操作',
      key: 'actions',
      render: (_, item) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => navigate(`/products/${item.id}/edit`)}>
          编辑
        </Button>
      ),
    })
  }

  return (
    <Card>
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>商品管理</Typography.Title>
          <Typography.Text type="secondary">查看商品并进入单品运营工作台</Typography.Text>
        </div>
        {canWrite && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/products/new')}>
            创建商品
          </Button>
        )}
      </div>
      {loading ? (
        <PageLoading />
      ) : error ? (
        <PageError message={error} onRetry={() => void load()} />
      ) : items.length === 0 ? (
        <PageEmpty description="暂无商品" />
      ) : (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Table rowKey="id" columns={columns} dataSource={items} pagination={false} />
          <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </Space>
      )}
    </Card>
  )
}
