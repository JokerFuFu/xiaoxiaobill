import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

// mock echarts,避免 jsdom 下 canvas 初始化问题;用 vi.hoisted 让 spy 在 vi.mock 提升后仍可引用
const { init, setOption, resize, dispose } = vi.hoisted(() => {
  const setOption = vi.fn()
  const resize = vi.fn()
  const dispose = vi.fn()
  const init = vi.fn(() => ({ setOption, resize, dispose }))
  return { init, setOption, resize, dispose }
})
vi.mock('echarts', () => ({ init }))

import EChart from '@/components/common/EChart.vue'

describe('EChart 封装', () => {
  beforeEach(() => vi.clearAllMocks())

  it('挂载即 echarts.init 并以 notMerge(true)方式 setOption', () => {
    const option = { series: [{ type: 'bar' }] }
    mount(EChart, { props: { option } })
    expect(init).toHaveBeenCalledTimes(1)
    expect(setOption).toHaveBeenCalledWith(option, true)
  })

  it('option 无数据(null)时不 setOption', () => {
    mount(EChart, { props: { option: null } })
    expect(init).toHaveBeenCalledTimes(1)
    expect(setOption).not.toHaveBeenCalled()
  })

  it('option 变化触发重绘', async () => {
    const wrapper = mount(EChart, { props: { option: { a: 1 } } })
    setOption.mockClear()
    await wrapper.setProps({ option: { a: 2 } })
    expect(setOption).toHaveBeenCalledWith({ a: 2 }, true)
  })

  it('卸载时 dispose 释放实例', () => {
    const wrapper = mount(EChart, { props: { option: { a: 1 } } })
    wrapper.unmount()
    expect(dispose).toHaveBeenCalledTimes(1)
  })
})
