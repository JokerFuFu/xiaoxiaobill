import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shouldRedirectToLogin, api } from '@/api/client'

// 动态 import('@/router') 命中此 mock,验证 401 走 router.push 而非 window.location
vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

describe('shouldRedirectToLogin', () => {
  it('401 且非登录页 → true', () => {
    expect(shouldRedirectToLogin(401, '/')).toBe(true)
    expect(shouldRedirectToLogin(401, '/transactions')).toBe(true)
  })

  it('401 但已在登录页 → false(避免跳转循环)', () => {
    expect(shouldRedirectToLogin(401, '/login')).toBe(false)
  })

  it('非 401 → false', () => {
    expect(shouldRedirectToLogin(200, '/')).toBe(false)
    expect(shouldRedirectToLogin(500, '/')).toBe(false)
  })
})

describe('401 处理走 vue-router', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('401 响应 → 抛「未登录」并 router.push(/login)', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 401,
      json: async () => ({ success: false, error: '未登录' }),
    })

    await expect(api.getAnomalies()).rejects.toThrow('未登录')

    const router = (await import('@/router')).default
    await vi.waitFor(() => expect(router.push).toHaveBeenCalledWith('/login'))
  })
})
