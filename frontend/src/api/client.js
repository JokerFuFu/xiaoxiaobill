// API 基础配置
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

/**
 * 统一 API 客户端
 * 复用现有后端 API，零修改后端代码
 */
export const api = {
  // ==================== 数据分析 API ====================
  /**
   * 获取年度分析数据
   * @param {Object} params - 查询参数 { year, min_amount, max_amount }
   */
  getYearlyAnalysis: (params) => get('/yearly_analysis', params),

  /**
   * 获取月度分析数据
   * @param {Object} params - 查询参数 { year, month }
   */
  getMonthlyAnalysis: (params) => get('/monthly_analysis', params),

  /**
   * 获取分类支出数据
   * @param {Object} params - 查询参数 { year, month }
   */
  getCategoryExpenses: (params) => get('/category_expenses', params),

  /**
   * 获取交易记录列表
   * @param {Object} params - 查询参数 { page, per_page, year, month, category, type, min_amount, max_amount, search }
   */
  getTransactions: (params) => get('/transactions', params),

  /**
   * 获取综合分析数据
   * @param {Object} params - 查询参数 { year }
   */
  getAnalysis: (params) => get('/analysis', params),

  /**
   * 获取渠道分析数据（银行卡/储蓄·信用/支付宝/微信）
   * @param {Object} params - 查询参数 { year, min_amount, max_amount }
   */
  getChannelAnalysis: (params) => get('/channel_analysis', params),

  /**
   * 获取时间分析数据
   * @param {Object} params - 查询参数 { year }
   */
  getTimeAnalysis: (params) => get('/time_analysis', params),

  /**
   * 获取每日数据（用于热力图）
   * @param {Object} params - 查询参数 { year, filter }
   */
  getDailyData: (params) => get('/daily_data', params),

  /**
   * 获取汇总数据
   */
  getSummary: () => get('/summary'),

  // ==================== 元数据 API ====================
  /**
   * 获取可用日期列表
   */
  getAvailableDates: () => get('/available_dates'),

  /**
   * 获取可用年份列表
   */
  getAvailableYears: () => get('/available_years'),

  /**
   * 获取所有分类
   */
  getCategories: () => get('/categories'),

  /**
   * 获取分类分析数据（带参数时获取具体分类数据，不带参数时获取分类列表）
   * @param {Object} params - 查询参数 { category, range, year, month, min_amount, max_amount }
   */
  getCategoryAnalysis: (params) => get('/category_analysis', params),

  /**
   * 获取分类分析的可用日期
   */
  getCategoryAvailableDates: () => get('/category_available_dates'),

  // ==================== 文件管理 API ====================
  /**
   * 上传文件
   * @param {FormData} formData - 文件数据
   */
  uploadFile: (formData) => post('/upload', formData),

  /**
   * 获取已上传文件列表
   */
  getFiles: () => get('/files'),

  /**
   * 删除文件
   * @param {string} filename - 文件名
   */
  deleteFile: (filename) => delete_(`/files/${filename}`),

  /**
   * 清除所有数据
   */
  clearData: () => post('/clear_data'),

  // ==================== 会话管理 API ====================
  /**
   * 进入演示模式
   */
  enterDemo: () => post('/demo/enter'),

  /**
   * 退出演示模式
   */
  exitDemo: () => post('/demo/exit'),

  /**
   * 获取会话状态 (特殊处理 - 后端返回格式不同)
   */
  getSessionStatus: () => getSessionStatus(),

  // ==================== 鉴权 / 用户管理 ====================
  authMe: () => get('/auth/me'),
  authBootstrap: () => get('/auth/bootstrap'),   // 首次安装引导:全新部署时带出默认账号
  login: (username, password) => post('/auth/login', { username, password }),
  logout: () => post('/auth/logout', {}),
  changePassword: (old_password, new_password) => post('/auth/password', { old_password, new_password }),
  adminListUsers: () => get('/admin/users'),
  adminCreateUser: (payload) => post('/admin/users', payload),
  adminDeleteUser: (uid) => delete_(`/admin/users/${uid}`),
  adminResetPassword: (uid, password) => post(`/admin/users/${uid}/password`, { password }),

  // ==================== 成员维度 ====================
  getMembers: () => get('/members'),
  addMember: (name, color) => post('/members', { name, color }),
  updateMember: (id, payload) => put(`/members/${id}`, payload),
  deleteMember: (id) => delete_(`/members/${id}`),
  getMemberAnalysis: (params) => get('/member_analysis', params),

  // ==================== AI ====================
  aiStatus: () => get('/ai/status'),
  aiChat: (question, history, chat_id, signal) => post('/ai/chat', { question, history, chat_id }, signal),
  aiChats: () => get('/ai/chats'),
  aiChatGet: (id) => get(`/ai/chats/${id}`),
  aiChatDelete: (id) => delete_(`/ai/chats/${id}`),
  aiChatRename: (id, title) => put(`/ai/chats/${id}`, { title }),
  aiRecognize: (formData) => post('/ai/recognize', formData),
  aiRecognizeText: (text, hint) => post('/ai/recognize', { text, hint }),
  aiRecognizeImport: (rows, member_id, name) => post('/ai/recognize/import', { rows, member_id, name }),
  aiGetConfig: () => get('/ai/config'),
  aiUpsertProfile: (payload) => post('/ai/profiles', payload),       // 新增/更新模型档案
  aiDeleteProfile: (pid) => delete_(`/ai/profiles/${pid}`),
  aiSaveRouting: (payload) => put('/ai/config', payload),            // 功能分配/默认档案/自定义供应商/自动分析
  aiTestConfig: (payload) => post('/ai/config/test', payload || {}),
  aiAnalyzeGet: (params) => get('/ai/analyze', params),             // 取缓存的智能分析
  aiAnalyzeRun: (payload) => post('/ai/analyze', payload),          // 触发生成智能分析

  // ==================== 首页概览 + 预算 ====================
  homeOverview: () => get('/home/overview'),
  budgetGet: () => get('/budget'),
  budgetSave: (payload) => post('/budget', payload),
  budgetStatus: (params) => get('/budget/status', params),

  // ==================== 收入分析 ====================
  getIncomeAnalysis: (params) => get('/income_analysis', params),

  // ==================== 邮箱取账单(通用 IMAP) ====================
  mailGetConfig: () => get('/mail/config'),
  mailSaveConfig: (payload) => post('/mail/config', payload),
  mailTest: () => post('/mail/test', {}),
  mailFetch: (days) => post('/mail/fetch', { days }),
  mailImport: (payload) => post('/mail/import', payload),

  // ==================== 账单洞察:订阅/境外/异常/年度账单 ====================
  getRecurring: (params) => get('/recurring', params),
  getOverseas: (params) => get('/overseas', params),
  getAnomalies: () => get('/anomalies'),
  getAnnualReport: (params) => get('/annual_report', params),
  genAnnualNarrative: (payload) => post('/annual_report/narrative', payload || {}),

  // ==================== 对账中心 / 资金性质口径 ====================
  getReconcile: (params) => get('/reconcile', params),
  natureRules: () => get('/nature/rules'),
  natureRulesSave: (rules) => post('/nature/rules', { rules }),

  // ==================== 资产负债(净资产) ====================
  networthGet: () => get('/networth'),
  networthAddAccount: (name, type) => post('/networth/accounts', { name, type }),
  networthUpdateAccount: (aid, payload) => put(`/networth/accounts/${aid}`, payload),
  networthDeleteAccount: (aid) => delete_(`/networth/accounts/${aid}`),
  networthSaveSnapshot: (date, balances, note) => post('/networth/snapshots', { date, balances, note }),
  networthDeleteSnapshot: (date) => delete_(`/networth/snapshots/${date}`)
}

// 401 未登录 → 跳登录页(登录页本身不跳,避免循环)
function _check401(response) {
  if (response.status === 401 && !window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
    throw new Error('未登录')
  }
}

// 统一 JSON 解析:网关超时/重启时上游会返回 HTML 错误页,直接 .json() 会抛
// "Unexpected token '<'" 这种天书 —— 这里转成人话
async function _parseJson(response) {
  try {
    return await response.json()
  } catch (e) {
    if (response.status === 504) {
      throw new Error('请求处理超时。如果是 AI 对话,回答通常已在后台完成并保存,刷新对话历史即可看到;也可以直接重试')
    }
    if (response.status === 502 || response.status === 503) {
      throw new Error('服务暂时不可用(可能正在重启),请稍后重试')
    }
    throw new Error(`服务响应异常(HTTP ${response.status}),请重试`)
  }
}

// ==================== 请求封装函数 ====================

/**
 * GET 请求
 * @param {string} endpoint - API 端点
 * @param {Object} params - 查询参数
 */
async function get(endpoint, params) {
  const url = new URL(API_BASE + endpoint, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    })
  }

  console.log('[API] GET request to:', url.toString())

  const response = await fetch(url, { credentials: 'same-origin' })
  _check401(response)
  const data = await _parseJson(response)

  console.log('[API] Response:', data)

  // 只在 success 字段存在且为 false 时才抛出错误
  // 有些端点（如 category_available_dates）不返回 success 字段
  if ('success' in data && !data.success) {
    throw new Error(data.error || '请求失败')
  }

  // 处理不同的响应格式
  // 有些端点返回 { success: true, data: {...} }
  // 有些端点返回 { success: true, years: [...] } 或其他直接数据
  if ('data' in data) {
    return data.data
  }

  // 如果没有 data 字段，返回整个响应对象（去掉 success 字段）
  const { success, ...result } = data
  return result
}

/**
 * POST 请求
 * @param {string} endpoint - API 端点
 * @param {Object|FormData} data - 请求数据
 */
async function post(endpoint, data, signal) {
  const isFormData = data instanceof FormData

  const response = await fetch(API_BASE + endpoint, {
    method: 'POST',
    credentials: 'same-origin',
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
    body: isFormData ? data : JSON.stringify(data),
    signal
  })
  _check401(response)

  const result = await _parseJson(response)

  // 只在 success 字段存在且为 false 时才抛出错误
  if ('success' in result && !result.success) {
    throw new Error(result.error || '请求失败')
  }

  // 处理不同的响应格式
  if ('data' in result) {
    return result.data
  }

  // 如果没有 data 字段，返回整个响应对象（去掉 success 字段）
  const { success, ...responseData } = result
  return responseData
}

/**
 * DELETE 请求
 * @param {string} endpoint - API 端点
 */
async function delete_(endpoint) {
  const response = await fetch(API_BASE + endpoint, {
    method: 'DELETE',
    credentials: 'same-origin'
  })
  _check401(response)

  const data = await _parseJson(response)

  // 只在 success 字段存在且为 false 时才抛出错误
  if ('success' in data && !data.success) {
    throw new Error(data.error || '请求失败')
  }

  // 处理不同的响应格式
  if ('data' in data) {
    return data.data
  }

  // 如果没有 data 字段，返回整个响应对象（去掉 success 字段）
  const { success, ...result } = data
  return result
}

/**
 * PUT 请求
 */
async function put(endpoint, data) {
  const response = await fetch(API_BASE + endpoint, {
    method: 'PUT',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {})
  })
  _check401(response)

  const result = await _parseJson(response)
  if ('success' in result && !result.success) {
    throw new Error(result.error || '请求失败')
  }
  if ('data' in result) {
    return result.data
  }
  const { success, ...responseData } = result
  return responseData
}

/**
 * 获取会话状态 (特殊处理)
 * 后端返回格式: { active: boolean, message: string }
 * 而不是标准的 { success: boolean, data: {...} }
 */
async function getSessionStatus() {
  console.log('[API] Getting session status...')
  try {
    const response = await fetch(API_BASE + '/session/status')
    const data = await response.json()
    console.log('[API] Session status response:', data)

    // 后端返回格式: { active: boolean, message: string }
    // 我们需要转换为前端期望的格式
    // 注意: 后端的 session/status 不返回 is_demo 字段
    // 所以我们需要通过其他方式判断演示模式
    return {
      active: data.active || false,
      message: data.message || '',
      // 由于后端不返回 is_demo，我们需要在客户端维护这个状态
      is_demo: false  // 这个值会在 session store 中被覆盖
    }
  } catch (error) {
    console.error('[API] Session status error:', error)
    // 出错时返回默认状态
    return {
      active: false,
      message: '获取会话状态失败',
      is_demo: false
    }
  }
}

export default api
