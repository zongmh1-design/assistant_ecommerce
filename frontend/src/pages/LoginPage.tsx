import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'

interface LoginValues {
  username: string
  password: string
}

export function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth()
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  if (!loading && isAuthenticated) return <Navigate to="/products" replace />

  const submit = async (values: LoginValues) => {
    setError('')
    setSubmitting(true)
    try {
      await login(values.username, values.password)
      const destination =
        typeof location.state === 'object' &&
        location.state !== null &&
        'from' in location.state &&
        typeof location.state.from === 'string'
          ? location.state.from
          : '/products'
      navigate(destination, { replace: true })
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '登录失败，请稍后重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <Card className="login-card">
        <Typography.Title level={2}>电商运营助手</Typography.Title>
        <Typography.Paragraph type="secondary">登录后进入单品运营工作台</Typography.Paragraph>
        {error && <Alert type="error" showIcon message={error} className="form-alert" />}
        <Form<LoginValues> layout="vertical" onFinish={submit}>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} autoComplete="username" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  )
}
