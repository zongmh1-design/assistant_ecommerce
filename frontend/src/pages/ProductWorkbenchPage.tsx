import { EditOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Descriptions, Menu, Result, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { getProduct } from '../api/products'
import { getStore } from '../api/stores'
import { useAuth } from '../auth/AuthContext'
import { PageError, PageLoading } from '../components/PageState'
import type { Product } from '../types/product'
import type { Store } from '../types/store'
import { SkuInventoryPage } from './SkuInventoryPage'
import { CompetitorsPage } from './CompetitorsPage'

const modules = [
  { key: 'overview', label: '概览', ready: true },
  { key: 'skus', label: 'SKU / 库存', ready: true },
  { key: 'competitors', label: '竞品', ready: true },
  { key: 'diagnosis', label: '商品诊断' },
  { key: 'creative-plans', label: '创意方案' },
  { key: 'generation-jobs', label: '生成任务' },
  { key: 'assets', label: '素材库' },
  { key: 'promotion-links', label: '推广链接' },
  { key: 'ad-recommendations', label: '投放建议' },
  { key: 'experiments', label: '投放实验' },
  { key: 'performance', label: '经营数据' },
  { key: 'review-reports', label: '复盘报告' },
]

export function ProductWorkbenchPage() {
  const { productId, moduleKey } = useParams()
  const navigate = useNavigate()
  const { canWrite } = useAuth()
  const [product, setProduct] = useState<Product | null>(null)
  const [store, setStore] = useState<Store | null>(null)
  const [error, setError] = useState('')
  const selected = moduleKey || 'overview'
  const currentModule = modules.find((item) => item.key === selected)

  useEffect(() => {
    const id = Number(productId)
    if (!Number.isInteger(id)) {
      setError('商品 ID 无效')
      return
    }
    getProduct(id)
      .then(async (value) => {
        setProduct(value)
        setStore(await getStore(value.store_id))
      })
      .catch((reason) => setError(reason instanceof ApiError ? reason.message : '商品工作台加载失败'))
  }, [productId])

  if (error) return <PageError message={error} />
  if (!product || !store) return <PageLoading />
  if (!currentModule) return <Result status="404" title="模块不存在" />

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card>
        <div className="page-heading">
          <div>
            <Typography.Title level={3}>{product.name}</Typography.Title>
            <Space>
              <Tag>{product.platform}</Tag>
              <Tag color={product.status === 'active' ? 'green' : 'default'}>{product.status}</Tag>
              <Typography.Text type="secondary">{store.store_name}</Typography.Text>
            </Space>
          </div>
          {canWrite && (
            <Button icon={<EditOutlined />} onClick={() => navigate(`/products/${product.id}/edit`)}>
              编辑商品
            </Button>
          )}
        </div>
      </Card>
      <Card className="workbench-card">
        <Menu
          mode="horizontal"
          selectedKeys={[selected]}
          items={modules.map((item) => ({
            key: item.key,
            label: item.label,
          }))}
          onClick={({ key }) => navigate(key === 'overview' ? `/products/${product.id}` : `/products/${product.id}/${key}`)}
        />
        <div className="workbench-content">
          {selected === 'overview' ? (
            <>
              <Typography.Title level={4}>商品概览</Typography.Title>
              <Descriptions bordered column={2}>
                <Descriptions.Item label="商品名称">{product.name}</Descriptions.Item>
                <Descriptions.Item label="所属店铺">{store.store_name}</Descriptions.Item>
                <Descriptions.Item label="平台">{product.platform}</Descriptions.Item>
                <Descriptions.Item label="分类">{product.category || '—'}</Descriptions.Item>
                <Descriptions.Item label="价格">¥{product.price}</Descriptions.Item>
                <Descriptions.Item label="成本">{product.cost ? `¥${product.cost}` : '—'}</Descriptions.Item>
                <Descriptions.Item label="目标人群" span={2}>{product.target_audience || '—'}</Descriptions.Item>
                <Descriptions.Item label="商品卖点" span={2}>
                  {product.selling_points.length ? product.selling_points.join('；') : '—'}
                </Descriptions.Item>
              </Descriptions>
              <Alert
                type="info"
                showIcon
                message="后续运营模块已预留导航入口"
                description="Phase 16A 只实现商品概览，其他模块将在后续前端阶段接入。"
                className="overview-note"
              />
            </>
          ) : selected === 'skus' ? (
            <SkuInventoryPage productId={product.id} />
          ) : selected === 'competitors' ? (
            <CompetitorsPage productId={product.id} />
          ) : (
            <Result
              status="info"
              title={currentModule.label}
              subTitle="此模块将在后续前端阶段实现，当前未发起任何业务 API 请求。"
            />
          )}
        </div>
      </Card>
    </Space>
  )
}
