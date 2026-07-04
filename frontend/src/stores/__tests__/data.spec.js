import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { api } from '@/api/client'
import { useDataStore } from '@/stores/data'

vi.mock('@/api/client', () => {
  // 命名导出 api 与默认导出共享同一 spy(store 用默认导入,测试用命名导入控制)
  const getAvailableYears = vi.fn()
  const shared = { getAvailableYears }
  return { api: shared, default: shared }
})

describe('dataStore.loadAvailableYears', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('解包 { years:[...] } 契约(移除 Array.isArray 兼容分支后仍正确)', async () => {
    api.getAvailableYears.mockResolvedValue({ years: [2024, 2023] })
    const store = useDataStore()
    const years = await store.loadAvailableYears()
    expect(years).toEqual([2024, 2023])
    expect(store.availableYears).toEqual([2024, 2023])
  })

  it('缺 years 字段 → 空数组', async () => {
    api.getAvailableYears.mockResolvedValue({})
    const store = useDataStore()
    expect(await store.loadAvailableYears()).toEqual([])
  })

  it('请求失败 → 返回空数组且不抛', async () => {
    api.getAvailableYears.mockRejectedValue(new Error('boom'))
    const store = useDataStore()
    expect(await store.loadAvailableYears()).toEqual([])
  })
})
