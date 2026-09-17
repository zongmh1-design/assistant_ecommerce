const TOKEN_KEY = 'ecommerce_access_token'
const DEFAULT_BASE_URL = '/api/v1'

export interface FieldErrorMap {
  [field: string]: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fieldErrors: FieldErrorMap

  constructor(
    status: number,
    code: string,
    message: string,
    fieldErrors: FieldErrorMap = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fieldErrors = fieldErrors
  }
}

let unauthorizedHandler: (() => void) | null = null

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function storeToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_KEY)
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function defaultMessage(status: number): string {
  if (status === 401) return '登录已失效，请重新登录'
  if (status === 403) return '当前账号无权执行此操作'
  if (status === 404) return '请求的资源不存在'
  if (status === 409) return '当前操作与已有数据冲突'
  if (status === 422) return '提交内容未通过校验'
  if (status >= 500) return '系统暂时不可用，请稍后重试'
  return '请求失败，请稍后重试'
}

function parseError(status: number, payload: unknown): ApiError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const code = typeof payload.error.code === 'string' ? payload.error.code : `http_${status}`
    const message = typeof payload.error.message === 'string' ? payload.error.message : defaultMessage(status)
    return new ApiError(status, code, message)
  }

  const fieldErrors: FieldErrorMap = {}
  if (isRecord(payload) && Array.isArray(payload.detail)) {
    for (const issue of payload.detail) {
      if (!isRecord(issue) || !Array.isArray(issue.loc)) continue
      const field = [...issue.loc].reverse().find((part) => typeof part === 'string' && part !== 'body')
      if (typeof field === 'string' && typeof issue.msg === 'string') fieldErrors[field] = issue.msg
    }
  }
  return new ApiError(status, `http_${status}`, defaultMessage(status), fieldErrors)
}

function buildUrl(path: string, query?: object): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
  const url = `${baseUrl}${path}`
  if (!query) return url
  const params = new URLSearchParams()
  Object.entries(query as Record<string, string | number | undefined>).forEach(([key, value]) => {
    if (value !== undefined) params.set(key, String(value))
  })
  const suffix = params.toString()
  return suffix ? `${url}?${suffix}` : url
}

export async function apiClient<T>(
  path: string,
  options: RequestInit = {},
  query?: object,
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const token = getStoredToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(buildUrl(path, query), { ...options, headers })
  } catch {
    throw new ApiError(0, 'network_error', '无法连接后端服务，请检查服务是否已启动')
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }

  if (!response.ok) {
    if (response.status === 401) unauthorizedHandler?.()
    throw parseError(response.status, payload)
  }
  return payload as T
}

/** 下载非 JSON 响应，同时复用认证和统一 HTTP 错误映射。 */
export async function apiClientBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const headers = new Headers(options.headers)
  headers.set('Accept', '*/*')
  const token = getStoredToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
    response = await fetch(`${baseUrl}${path}`, { ...options, headers })
  } catch {
    throw new ApiError(0, 'network_error', '无法连接后端服务，请检查服务是否已启动')
  }

  if (!response.ok) {
    const text = await response.text()
    let payload: unknown = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        payload = null
      }
    }
    if (response.status === 401) unauthorizedHandler?.()
    throw parseError(response.status, payload)
  }
  return response.blob()
}
