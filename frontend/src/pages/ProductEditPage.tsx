import { Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { getProduct, updateProduct } from '../api/products'
import { ProductForm } from '../components/ProductForm'
import { PageError, PageLoading } from '../components/PageState'
import type { Product, ProductCreate, ProductUpdate } from '../types/product'

function changedFields(original: Product, next: ProductCreate): ProductUpdate {
  const result: ProductUpdate = {}
  const comparable: Array<keyof ProductCreate> = [
    'store_id',
    'name',
    'platform',
    'category',
    'price',
    'cost',
    'target_audience',
    'selling_points',
    'product_url',
    'images_json',
    'status',
  ]
  for (const key of comparable) {
    if (JSON.stringify(original[key]) !== JSON.stringify(next[key])) {
      Object.assign(result, { [key]: next[key] })
    }
  }
  return result
}

export function ProductEditPage() {
  const { productId } = useParams()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const id = Number(productId)
    if (!Number.isInteger(id)) {
      setError('商品 ID 无效')
      return
    }
    getProduct(id)
      .then(setProduct)
      .catch((reason) => setError(reason instanceof ApiError ? reason.message : '商品加载失败'))
  }, [productId])

  if (error) return <PageError message={error} />
  if (!product) return <PageLoading />

  return (
    <>
      <Typography.Title level={3}>编辑商品</Typography.Title>
      <ProductForm
        product={product}
        submitText="保存修改"
        onCancel={() => navigate(`/products/${product.id}`)}
        onSubmit={async (data) => {
          const patch = changedFields(product, data)
          if (Object.keys(patch).length) await updateProduct(product.id, patch)
          navigate(`/products/${product.id}`, { replace: true })
        }}
      />
    </>
  )
}
