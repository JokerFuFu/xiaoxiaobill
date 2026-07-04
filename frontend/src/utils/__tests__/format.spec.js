import { describe, it, expect } from 'vitest'
import { formatMoney, formatTime, getCategoryColor } from '@/utils/format'

describe('formatMoney', () => {
  it('千分位 + 两位小数', () => {
    expect(formatMoney(1234.5)).toBe('1,234.50')
  })

  it('整数补两位小数', () => {
    expect(formatMoney(1000)).toBe('1,000.00')
  })
})

describe('formatTime', () => {
  it('负数/零 → 0秒', () => {
    expect(formatTime(0)).toBe('0秒')
    expect(formatTime(-5)).toBe('0秒')
  })

  it('时分秒组合', () => {
    expect(formatTime(3661)).toBe('1小时1分钟1秒')
  })
})

describe('getCategoryColor', () => {
  it('未知分类回退到「其他」色', () => {
    expect(getCategoryColor('不存在的分类')).toBe(getCategoryColor('其他'))
  })
})
