import {
  LogoutOutlined,
  ShopOutlined,
  ShoppingOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Layout, Menu, Space, Tag, Typography } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const { Header, Sider, Content } = Layout

const roleLabels = {
  admin: '管理员',
  operator: '运营人员',
  viewer: '查看人员',
}

export function AppLayout() {
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const selectedKey = location.pathname.startsWith('/stores') ? '/stores' : '/products'

  return (
    <Layout className="app-shell">
      <Sider width={220} theme="light" className="app-sider">
        <div className="brand">
          <ShoppingOutlined />
          <span>电商运营助手</span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/stores', icon: <ShopOutlined />, label: '店铺管理' },
            { key: '/products', icon: <ShoppingOutlined />, label: '商品管理' },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Text type="secondary">单品运营工作台</Typography.Text>
          <Space>
            <Avatar icon={<UserOutlined />} />
            <span>{currentUser?.display_name || currentUser?.username}</span>
            {currentUser && <Tag color={currentUser.role === 'viewer' ? 'default' : 'blue'}>{roleLabels[currentUser.role]}</Tag>}
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={() => {
                logout()
                navigate('/login', { replace: true })
              }}
            >
              退出
            </Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
