import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'

export function NotFoundPage() {
  const navigate = useNavigate()
  return <Result status="404" title="页面不存在" extra={<Button onClick={() => navigate('/products')}>返回商品列表</Button>} />
}
