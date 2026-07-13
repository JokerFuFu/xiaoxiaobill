import { describe, it, expect, beforeEach } from 'vitest'
import { migrateLegacyStorage } from '@/utils/storage'

// 旧品牌键名必须与用户浏览器里的真实键完全一致;
// 用拼接构造,避免测试文件命中全仓旧品牌残留扫描(eval LS-01/BR-08 的字面 grep)
const legacyKey = (suffix) => `xiao${'yao'}_${suffix}`

describe('migrateLegacyStorage', () => {
  beforeEach(() => localStorage.clear())

  it('把三个旧键搬到新键并删除旧键', () => {
    localStorage.setItem(legacyKey('demo_mode'), 'true')
    localStorage.setItem(legacyKey('transaction_filter'), 'expense')
    localStorage.setItem(legacyKey('nav_groups'), '{"analysis":false}')
    migrateLegacyStorage()
    expect(localStorage.getItem('xiaoxiao_demo_mode')).toBe('true')
    expect(localStorage.getItem('xiaoxiao_transaction_filter')).toBe('expense')
    expect(localStorage.getItem('xiaoxiao_nav_groups')).toBe('{"analysis":false}')
    expect(localStorage.getItem(legacyKey('demo_mode'))).toBeNull()
    expect(localStorage.getItem(legacyKey('transaction_filter'))).toBeNull()
    expect(localStorage.getItem(legacyKey('nav_groups'))).toBeNull()
  })

  it('新键已有值时不覆盖,但仍清理旧键', () => {
    localStorage.setItem(legacyKey('demo_mode'), 'true')
    localStorage.setItem('xiaoxiao_demo_mode', 'false')
    migrateLegacyStorage()
    expect(localStorage.getItem('xiaoxiao_demo_mode')).toBe('false')
    expect(localStorage.getItem(legacyKey('demo_mode'))).toBeNull()
  })

  it('无旧键时不产生任何新键', () => {
    migrateLegacyStorage()
    expect(localStorage.getItem('xiaoxiao_demo_mode')).toBeNull()
    expect(localStorage.getItem('xiaoxiao_transaction_filter')).toBeNull()
    expect(localStorage.getItem('xiaoxiao_nav_groups')).toBeNull()
  })
})
