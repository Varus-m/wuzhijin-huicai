/**
 * 工具函数导出
 */

export * from './user'
export * from './api'

/**
 * 格式化时间
 */
export function formatTime(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

/**
 * 格式化日期
 */
export function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  
  return `${year}-${month}-${day}`
}

/**
 * 格式化相对时间
 */
export function formatRelativeTime(timestamp: number): string {
  const now = Date.now()
  const diff = now - timestamp
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day
  const year = 365 * day
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < week) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < month) {
    return `${Math.floor(diff / week)}周前`
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`
  } else {
    return `${Math.floor(diff / year)}年前`
  }
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  
  return function (...args: Parameters<T>) {
    if (timeout) {
      clearTimeout(timeout)
    }
    
    timeout = setTimeout(() => {
      func.apply(this, args)
    }, wait)
  }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  
  return function (...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}

/**
 * 深拷贝
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as unknown as T
  }
  
  if (typeof obj === 'object') {
    const cloned = {} as T
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        cloned[key] = deepClone(obj[key])
      }
    }
    return cloned
  }
  
  return obj
}

/**
 * 判断是否为手机号
 */
export function isPhoneNumber(phone: string): boolean {
  return /^1[3-9]\d{9}$/.test(phone)
}

/**
 * 判断是否为邮箱
 */
export function isEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

/**
 * 生成随机字符串
 */
export function generateRandomString(length: number = 8): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 获取订单状态颜色
 */
export function getOrderStatusColor(status: string): string {
  const statusColors: Record<string, string> = {
    'pending': '#FF9800',     // 待处理 - 橙色
    'processing': '#2196F3', // 处理中 - 蓝色
    'producing': '#9C27B0',  // 生产中 - 紫色
    'shipped': '#00BCD4',    // 已发货 - 青色
    'delivered': '#4CAF50',  // 已送达 - 绿色
    'cancelled': '#F44336',  // 已取消 - 红色
    'completed': '#607D8B'   // 已完成 - 灰色
  }
  
  return statusColors[status] || '#666666'
}

/**
 * 获取订单状态文本
 */
export function getOrderStatusText(status: string): string {
  const statusTexts: Record<string, string> = {
    'pending': '待处理',
    'processing': '处理中',
    'producing': '生产中',
    'shipped': '已发货',
    'delivered': '已送达',
    'cancelled': '已取消',
    'completed': '已完成'
  }
  
  return statusTexts[status] || status
}

/**
 * 显示加载提示
 */
export function showLoading(title: string = '加载中...'): void {
  wx.showLoading({
    title,
    mask: true
  })
}

/**
 * 隐藏加载提示
 */
export function hideLoading(): void {
  wx.hideLoading()
}

/**
 * 显示成功提示
 */
export function showSuccess(title: string, duration: number = 2000): void {
  wx.showToast({
    title,
    icon: 'success',
    duration
  })
}

/**
 * 显示错误提示
 */
export function showError(title: string, duration: number = 2000): void {
  wx.showToast({
    title,
    icon: 'error',
    duration
  })
}

/**
 * 显示模态对话框
 */
export function showModal(
  title: string,
  content: string,
  showCancel: boolean = true,
  confirmText: string = '确定',
  cancelText: string = '取消'
): Promise<boolean> {
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      showCancel,
      confirmText,
      cancelText,
      success: (res) => {
        resolve(res.confirm)
      },
      fail: () => {
        resolve(false)
      }
    })
  })
}