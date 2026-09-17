export type UserRole = 'admin' | 'operator' | 'viewer'

export interface User {
  id: number
  username: string
  display_name: string
  role: UserRole
  status: 'active' | 'disabled'
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
}
