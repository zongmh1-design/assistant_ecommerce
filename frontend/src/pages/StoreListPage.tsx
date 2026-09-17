import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { App, Button, Card, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { createStore, listStores, updateStore } from '../api/stores'
import { useAuth } from '../auth/AuthContext'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import { StoreFormModal } from '../components/StoreFormModal'
import type { Store, StoreCreate } from '../types/store'

const PAGE_SIZE = 10
const platformLabels: Record<string, string> = {
  taobao: '淘宝',
  tmall: '天猫',
  jd: '京东',
  douyin: '抖音',
  pinduoduo: '拼多多',
  other: '其他',
}

export function StoreListPage() {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<Store[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<Store | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listStores({ page, page_size: PAGE_SIZE })
      setItems(result.items)
      setTotal(result.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '店铺列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    void load()
  }, [load])

  const columns: ColumnsType<Store> = [
    { title: '店铺名称', dataIndex: 'store_name' },
    { title: '平台', dataIndex: 'platform', render: (value: string) => <Tag>{platformLabels[value] || value}</Tag> },
    { title: '负责人', dataIndex: 'owner_name', render: (value: string | null) => value || '—' },
    { title: '平台店铺 ID', dataIndex: 'external_store_id', render: (value: string | null) => value || '—' },
    { title: '创建时间', dataIndex: 'created_at', render: (value: string) => new Date(value).toLocaleString('zh-CN') },
  ]
  if (canWrite) {
    columns.push({
      title: '操作',
      key: 'actions',
      render: (_, store) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => {
            setEditing(store)
            setModalOpen(true)
          }}
        >
          编辑
        </Button>
      ),
    })
  }

  return (
    <Card>
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>店铺管理</Typography.Title>
          <Typography.Text type="secondary">维护商品所属店铺与平台信息</Typography.Text>
        </div>
        {canWrite && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditing(null)
              setModalOpen(true)
            }}
          >
            创建店铺
          </Button>
        )}
      </div>
      {loading ? (
        <PageLoading />
      ) : error ? (
        <PageError message={error} onRetry={() => void load()} />
      ) : items.length === 0 ? (
        <PageEmpty description="暂无店铺" />
      ) : (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Table rowKey="id" columns={columns} dataSource={items} pagination={false} />
          <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </Space>
      )}
      <StoreFormModal
        open={modalOpen}
        store={editing}
        onCancel={() => setModalOpen(false)}
        onSubmit={async (data: StoreCreate) => {
          if (editing) await updateStore(editing.id, data)
          else await createStore(data)
          setModalOpen(false)
          message.success(editing ? '店铺已更新' : '店铺已创建')
          await load()
        }}
      />
    </Card>
  )
}
