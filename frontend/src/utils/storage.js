// localStorage 品牌前缀迁移:xiaoyao_* → xiaoxiao_*(2026-07 品牌化)
// 目的:改名不丢用户本地偏好(演示模式/交易筛选/导航折叠状态)
const LEGACY_KEY_MAP = {
  xiaoyao_demo_mode: 'xiaoxiao_demo_mode',
  xiaoyao_transaction_filter: 'xiaoxiao_transaction_filter',
  xiaoyao_nav_groups: 'xiaoxiao_nav_groups',
}

/**
 * 迁移旧品牌前缀的 localStorage 键(幂等)
 * @param {Storage} storage - 默认 window.localStorage,测试可注入
 */
export function migrateLegacyStorage(storage = localStorage) {
  for (const [oldKey, newKey] of Object.entries(LEGACY_KEY_MAP)) {
    try {
      const val = storage.getItem(oldKey)
      if (val !== null) {
        if (storage.getItem(newKey) === null) storage.setItem(newKey, val)
        storage.removeItem(oldKey)
      }
    } catch (e) {
      // 隐私模式等 localStorage 不可用场景:静默跳过
    }
  }
}
