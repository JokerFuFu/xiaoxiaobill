// vitest 全局 setup
// Node ≥23 自带的 webstorage 全局(localStorage)在未指定 --localstorage-file 时
// 只是不可用的占位对象,且会遮蔽 jsdom 的实现——这里统一替换为内存版 Storage,
// 保证测试中 localStorage 行为与浏览器一致
function createMemoryStorage() {
  let store = new Map()
  return {
    getItem: (k) => (store.has(String(k)) ? store.get(String(k)) : null),
    setItem: (k, v) => store.set(String(k), String(v)),
    removeItem: (k) => store.delete(String(k)),
    clear: () => store.clear(),
    key: (i) => [...store.keys()][i] ?? null,
    get length() {
      return store.size
    },
  }
}

const memoryStorage = createMemoryStorage()
Object.defineProperty(globalThis, 'localStorage', {
  value: memoryStorage,
  configurable: true,
  writable: true,
})
if (typeof window !== 'undefined' && window !== globalThis) {
  Object.defineProperty(window, 'localStorage', {
    value: memoryStorage,
    configurable: true,
    writable: true,
  })
}
