import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import DataTable from '@/components/common/DataTable.vue'

const columns = [
  { key: 'name', label: '名称' },
  { key: 'amount', label: '金额', align: 'right', formatter: (v) => '¥' + v },
]

describe('DataTable 封装', () => {
  it('渲染表头与数据行', () => {
    const rows = [{ name: 'A', amount: 10 }, { name: 'B', amount: 20 }]
    const w = mount(DataTable, { props: { columns, rows } })
    expect(w.findAll('thead th')).toHaveLength(2)
    expect(w.findAll('tbody tr')).toHaveLength(2)
    expect(w.text()).toContain('名称')
  })

  it('列 formatter 生效', () => {
    const w = mount(DataTable, { props: { columns, rows: [{ name: 'A', amount: 10 }] } })
    expect(w.text()).toContain('¥10')
  })

  it('无数据显示空态', () => {
    const w = mount(DataTable, { props: { columns, rows: [], emptyText: '没有记录' } })
    expect(w.find('.data-table-empty').text()).toBe('没有记录')
  })

  it('具名单元格插槽覆盖默认渲染', () => {
    const w = mount(DataTable, {
      props: { columns, rows: [{ name: 'A', amount: 10 }] },
      slots: { 'cell-name': '<span class="custom">自定义</span>' },
    })
    expect(w.find('.custom').text()).toBe('自定义')
  })
})
