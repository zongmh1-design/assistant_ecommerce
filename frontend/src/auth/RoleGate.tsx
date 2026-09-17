import type { PropsWithChildren } from 'react'
import { useAuth } from './AuthContext'

export function WriteRoleGate({ children }: PropsWithChildren) {
  return useAuth().canWrite ? children : null
}
