/**
 * API请求工具函数
 */

// import { getUserOpenid } from './user'

/**
 * 获取微信登录code
 */
export async function getWechatLoginCode(): Promise<string> {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => {
        if (res.code) {
          resolve(res.code)
        } else {
          reject(new Error('获取微信登录code失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * API基础配置
 */
const API_CONFIG = {
  baseURL: 'http://localhost:5000', // 本地开发环境地址
  timeout: 10000,
  retryCount: 3,
  retryDelay: 1000
}

/**
 * 请求拦截器
 */
function requestInterceptor(config: any) {
  const session = wx.getStorageSync('session')
  const token = session?.token
  
  if (token) {
    config.header = config.header || {}
    config.header['Authorization'] = `Bearer ${token}`
  }
  return config
}

/**
 * 响应拦截器
 */
function responseInterceptor(response: any) {
  if (response.statusCode === 401) {
    wx.removeStorageSync('session')
    wx.reLaunch({ url: '/pages/login/login' })
    const err: any = new Error(response.data?.message || '登录已过期')
    err.code = 401
    err.data = response.data
    return Promise.reject(err)
  }
  if (response.statusCode >= 400) {
    const err: any = new Error(response.data?.message || '请求失败')
    err.code = response.statusCode
    err.data = response.data
    return Promise.reject(err)
  }
  
  return response.data
}

/**
 * 通用请求函数（带重试机制）
 */
export async function request(options: WechatMiniprogram.RequestOption): Promise<any> {
  const config = requestInterceptor(options)
  
  let retryCount = 0
  
  async function doRequest(): Promise<any> {
    try {
      const response = await new Promise<WechatMiniprogram.RequestSuccessCallbackResult>((resolve, reject) => {
        wx.request({
          ...config,
          url: config.url.startsWith('http') ? config.url : `${API_CONFIG.baseURL}${config.url}`,
          timeout: config.timeout || API_CONFIG.timeout,
          success: resolve,
          fail: reject
        })
      })
      
      return responseInterceptor(response)
    } catch (error) {
      if (retryCount < API_CONFIG.retryCount) {
        retryCount++
        console.warn(`请求失败，第${retryCount}次重试:`, error)
        
        // 延迟重试
        await new Promise(resolve => setTimeout(resolve, API_CONFIG.retryDelay * retryCount))
        return doRequest()
      }
      
      throw error
    }
  }
  
  return doRequest()
}

/**
 * 用户相关API
 */
export const userAPI = {
  /**
   * 获取用户信息
   */
  async getProfile(userId: string) {
    return request({
      url: '/api/user/profile',
      method: 'GET',
      data: {}
    })
  },

  /**
   * 绑定企业
   */
  async bindCompany(inviteCode: string) {
    const session = wx.getStorageSync('session') || {}
    return request({
      url: '/api/auth/bind-company',
      method: 'POST',
      data: {
        inviteCode,
        userId: session.userId
      }
    })
  }
}

/**
 * 订单相关API
 */
export const orderAPI = {
  /**
   * 搜索订单
   */
  async searchOrders(params: {
    keyword?: string,
    status?: string,
    page?: number,
    pageSize?: number
  }) {
    const session = wx.getStorageSync('session') || {}
    if (!session?.token) throw new Error('用户未登录')
    
    return request({
      url: '/api/orders/search',
      method: 'GET',
      data: { ...params }
    })
  },
  
  /**
   * 获取订单详情
   */
  async getOrderDetail(orderNo: string) {
    return request({
      url: `/api/orders/${orderNo}/detail`,
      method: 'GET'
    })
  },
  
  /**
   * 获取订单物料
   */
  async getOrderMaterials(orderId: string) {
    return request({
      url: `/api/orders/${orderId}/materials`,
      method: 'GET'
    })
  },
  
  /**
   * 获取物料进度
   */
  async getMaterialProgress(materialId: string) {
    return request({
      url: `/api/materials/${materialId}/progress`,
      method: 'GET'
    })
  }
}

/**
 * 消息相关API
 */
export const messageAPI = {
  /**
   * 发送模板消息
   */
  async sendTemplateMessage(data: {
    templateId: string,
    data: object,
    page?: string
  }) {
    const session = wx.getStorageSync('session') || {}
    if (!session?.token) throw new Error('用户未登录')
    
    return request({
      url: '/api/wechat/template-msg',
      method: 'POST',
      data: { ...data }
    })
  },
  
  /**
   * 获取消息记录
   */
  async getMessageHistory(page: number = 1, pageSize: number = 20, type?: string) {
    const session = wx.getStorageSync('session') || {}
    const userId = session.userId
    if (!userId) throw new Error('用户未登录')
    
    return request({
      url: '/api/messages/history',
      method: 'GET',
      data: {
        userId,
        page,
        pageSize,
        type
      }
    })
  },

  /**
   * 标记消息为已读
   */
  async markAsRead(messageId: string) {
    const session = wx.getStorageSync('session') || {}
    const userId = session.userId
    if (!userId) throw new Error('用户未登录')
    
    return request({
      url: '/api/messages/mark-read',
      method: 'POST',
      data: {
        userId,
        messageId
      }
    })
  },

  /**
   * 标记所有消息为已读
   */
  async markAllRead() {
    const session = wx.getStorageSync('session') || {}
    const userId = session.userId
    if (!userId) throw new Error('用户未登录')
    
    return request({
      url: '/api/messages/mark-all-read',
      method: 'POST',
      data: {
        userId
      }
    })
  },

  /**
   * 清空所有消息
   */
  async clearAll() {
    const session = wx.getStorageSync('session') || {}
    const userId = session.userId
    if (!userId) throw new Error('用户未登录')
    
    return request({
      url: '/api/messages/clear-all',
      method: 'POST',
      data: {
        userId
      }
    })
  }
}



/**
 * 上传文件
 */
export async function uploadFile(filePath: string, data?: any): Promise<any> {
  const session = wx.getStorageSync('session') || {}
  if (!session?.token) throw new Error('用户未登录')
  
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${API_CONFIG.baseURL}/api/upload`,
      filePath,
      name: 'file',
      formData: {
        ...data
      },
      success: resolve,
      fail: reject
    })
  })
}
