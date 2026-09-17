import { Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { createProduct } from '../api/products'
import { ProductForm } from '../components/ProductForm'

export function ProductCreatePage() {
  const navigate = useNavigate()
  return (
    <>
      <Typography.Title level={3}>创建商品</Typography.Title>
      <ProductForm
        submitText="创建商品"
        onCancel={() => navigate('/products')}
        onSubmit={async (data) => {
          const created = await createProduct(data)
          navigate(`/products/${created.id}`, { replace: true })
        }}
      />
    </>
  )
}
