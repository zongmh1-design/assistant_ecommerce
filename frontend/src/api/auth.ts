import { apiClient } from './client'
import type { LoginResponse, User } from '../types/auth'

export function login(username: string, password: string): Promise<LoginResponse> {
  return apiClient<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function getCurrentUser(): Promise<User> {
  return apiClient<User>('/auth/me')
}
