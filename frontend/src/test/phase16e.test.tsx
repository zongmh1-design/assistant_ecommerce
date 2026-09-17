import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App as AntdApp } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { PromotionLinksPage } from '../pages/PromotionLinksPage'
import type {
  PromotionLink,
  PromotionLinkClick,
  PromotionLinkSuggestion,
} from '../types/promotionLink'

const mocks = vi.hoisted(() => ({
  generatePromotionSuggestion: vi.fn(),
  createPromotionLink: vi.fn(),
  listPromotionLinks: vi.fn(),
  getPromotionLink: vi.fn(),
  updatePromotionLink: vi.fn(),
  listPromotionLinkClicks: vi.fn(),
}))
const authState = vi.hoisted(() => ({ canWrite: true }))

vi.mock('../api/promotionLinks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/promotionLinks')>()
  return {
    ...actual,
    generatePromotionSuggestion: mocks.generatePromotionSuggestion,
    createPromotionLink: mocks.createPromotionLink,
    listPromotionLinks: mocks.listPromotionLinks,
    getPromotionLink: mocks.getPromotionLink,
    updatePromotionLink: mocks.updatePromotionLink,
    listPromotionLinkClicks: mocks.listPromotionLinkClicks,
  }
})
vi.mock('../auth/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../auth/AuthContext')>()
  return { ...actual, useAuth: () => authState }
})
vi.mock('../components/PromotionLinkFormModal', async () => {
  const React = await import('react')
  return {
    PromotionLinkFormModal: ({
      open,
      link,
      suggestion,
      onCancel,
      onSubmit,
    }: {
      open: boolean
      link: PromotionLink | null
      suggestion?: PromotionLinkSuggestion | null
      onCancel: () => void
      onSubmit: (data: Record<string, unknown>) => Promise<void>
    }) => open ? React.createElement(
      'section',
      { role: 'dialog', 'aria-label': link ? '编辑推广链接' : '创建正式推广链接' },
      React.createElement('div', null, suggestion ? 'target URL 需要人工填写' : ''),
      React.createElement('button', {
        onClick: () => void onSubmit(link
          ? { link_name: '人工修改链接' }
          : {
            link_name: suggestion?.link_name || '手工推广链接',
            target_url: 'https://shop.example.com/product/20',
            scene_text: suggestion?.scene_text || '商品详情页',
            utm_json: {
              utm_source: suggestion?.utm_source || 'manual',
              utm_medium: suggestion?.utm_medium || 'link',
              utm_campaign: suggestion?.utm_campaign || 'demo',
              utm_content: suggestion?.utm_content || 'manual',
            },
          }),
      }, link ? '保存推广链接' : '创建正式链接'),
      React.createElement('button', { onClick: onCancel }, '取消'),
    ) : null,
  }
})
vi.mock('../components/PromotionLinkDetailDrawer', async () => {
  const React = await import('react')
  const buildTrackingUrl = (trackingCode: string) => `/api/v1/r/${trackingCode}`
  return {
    PromotionLinkDetailDrawer: ({
      productId,
      link,
      open,
      onClose,
      onEdit,
    }: {
      productId: number
      link: PromotionLink | null
      open: boolean
      canWrite: boolean
      onClose: () => void
      onEdit?: (value: PromotionLink) => void
    }) => {
      React.useEffect(() => {
        if (open && link) void mocks.listPromotionLinkClicks(productId, link.id, { page: 1, page_size: 10 })
      }, [link, open, productId])
      if (!open || !link) return null
      return React.createElement(
        'section',
        { role: 'dialog', 'aria-label': '推广链接详情' },
        React.createElement('div', null, '公开 tracking 跳转入口'),
        React.createElement('div', null, 'Mozilla/5.0 Demo'),
        React.createElement('button', { onClick: () => window.open(buildTrackingUrl(link.tracking_code), '_blank') }, '测试跳转'),
        React.createElement('button', { onClick: () => onEdit?.(link) }, '编辑推广链接'),
        React.createElement('button', { onClick: onClose }, '关闭'),
      )
    },
  }
})

const suggestion: PromotionLinkSuggestion = {
  link_name: '秋季社媒推广',
  scene_text: '社交媒体分享',
  utm_source: 'xiaohongshu',
  utm_medium: 'social',
  utm_campaign: 'autumn_demo',
  utm_content: 'main_image_v1',
  rationale: '便于区分社媒素材带来的访问。',
}
const link: PromotionLink = {
  id: 61,
  product_id: 20,
  link_name: '秋季社媒推广',
  target_url: 'https://shop.example.com/product/20',
  tracking_code: 'trkDemo61',
  utm_json: {
    utm_source: 'xiaohongshu',
    utm_medium: 'social',
    utm_campaign: 'autumn_demo',
    utm_content: 'main_image_v1',
  },
  status: 'active',
  click_count: 4,
  scene_text: '社交媒体分享',
  created_at: '2026-09-17T02:00:00Z',
  updated_at: '2026-09-17T02:00:00Z',
}
const click: PromotionLinkClick = {
  id: 71,
  promotion_link_id: 61,
  clicked_at: '2026-09-17T02:10:00Z',
  client_ip: null,
  user_agent: 'Mozilla/5.0 Demo',
}

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 20 }
}

function renderPage() {
  return render(<AntdApp><MemoryRouter><PromotionLinksPage productId={20} /></MemoryRouter></AntdApp>)
}

beforeEach(() => {
  vi.clearAllMocks()
  authState.canWrite = true
  mocks.listPromotionLinks.mockResolvedValue(page([link]))
  mocks.getPromotionLink.mockResolvedValue(link)
  mocks.listPromotionLinkClicks.mockResolvedValue(page([click]))
  mocks.generatePromotionSuggestion.mockResolvedValue(suggestion)
  mocks.createPromotionLink.mockResolvedValue({ ...link, id: 62, tracking_code: 'trkDemo62' })
  mocks.updatePromotionLink.mockResolvedValue({ ...link, link_name: '人工修改链接' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('PromotionLink frontend', () => {
  it('generates a visible suggestion without creating a formal link', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /生成推广建议/ }))
    expect(await screen.findByText('AI 推广参数建议（仅建议，尚未创建正式链接）')).toBeInTheDocument()
    expect(screen.getAllByText('秋季社媒推广').length).toBeGreaterThan(0)
    expect(mocks.createPromotionLink).not.toHaveBeenCalled()
  })

  it('keeps suggestion loading disabled and surfaces a safe provider error', async () => {
    let resolveSuggestion: ((value: PromotionLinkSuggestion) => void) | undefined
    mocks.generatePromotionSuggestion.mockReturnValue(new Promise((resolve) => { resolveSuggestion = resolve }))
    renderPage()
    const button = await screen.findByRole('button', { name: /生成推广建议/ })
    fireEvent.click(button)
    expect(button).toHaveAttribute('disabled')
    resolveSuggestion?.(suggestion)
    await waitFor(() => expect(mocks.generatePromotionSuggestion).toHaveBeenCalledWith(20))

    mocks.generatePromotionSuggestion.mockRejectedValue(new ApiError(502, 'invalid_llm_output', '模型输出格式不正确'))
    fireEvent.click(button)
    expect(await screen.findByText('模型输出格式不正确')).toBeInTheDocument()
    expect(screen.queryByText(/API Key|Authorization|traceback/i)).not.toBeInTheDocument()
  })

  it('uses a suggestion to prefill a create flow but requires an explicit target URL', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /生成推广建议/ }))
    fireEvent.click(await screen.findByRole('button', { name: '使用此建议创建链接' }))
    expect(await screen.findByText('target URL 需要人工填写')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '创建正式链接' }))
    await waitFor(() => expect(mocks.createPromotionLink).toHaveBeenCalledWith(20, expect.objectContaining({
      target_url: 'https://shop.example.com/product/20',
      link_name: suggestion.link_name,
    })))
    const payload = mocks.createPromotionLink.mock.calls[0][1] as Record<string, unknown>
    expect(payload).not.toHaveProperty('tracking_code')
    expect(payload).not.toHaveProperty('click_count')
  })

  it('shows list/detail/click records and opens the public tracking URL', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    renderPage()
    await waitFor(() => expect(document.body.textContent).toContain('秋季社媒推广'), { timeout: 10000 })
    expect(screen.getAllByText('累计点击', { exact: false }).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: '查看详情' }))
    expect(await screen.findByText('公开 tracking 跳转入口')).toBeInTheDocument()
    expect(mocks.listPromotionLinkClicks).toHaveBeenCalledWith(20, 61, { page: 1, page_size: 10 })
    fireEvent.click(screen.getByRole('button', { name: /测试跳转/ }))
    expect(openSpy).toHaveBeenCalledWith(expect.stringContaining('/api/v1/r/trkDemo61'), '_blank')
  }, 30000)

  it('edits a link through PATCH and keeps viewer read-only', async () => {
    const firstRender = renderPage()
    await waitFor(() => expect(document.body.textContent).toContain('秋季社媒推广'), { timeout: 10000 })
    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0])
    fireEvent.click(await screen.findByRole('button', { name: '保存推广链接' }))
    await waitFor(() => expect(mocks.updatePromotionLink).toHaveBeenCalledWith(20, 61, { link_name: '人工修改链接' }))

    authState.canWrite = false
    firstRender.unmount()
    renderPage()
    await waitFor(() => expect(document.body.textContent).toContain('秋季社媒推广'), { timeout: 10000 })
    expect(screen.queryByRole('button', { name: /生成推广建议/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /创建推广链接/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /编辑/ })).not.toBeInTheDocument()
  }, 30000)

  it('renders an explicit empty state', async () => {
    mocks.listPromotionLinks.mockResolvedValue(page([]))
    renderPage()
    expect(await screen.findByText('当前商品暂无推广链接')).toBeInTheDocument()
  })
})
