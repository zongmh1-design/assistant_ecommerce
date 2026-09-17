import { Result } from 'antd'
import { Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function WriteRoute() {
  return useAuth().canWrite ? <Outlet /> : <Result status="403" title="无权限" subTitle="当前角色只能查看数据" />
}
