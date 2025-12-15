import { request } from './api'

/**
 * 用户相关工具函数
 */

/**
 * 获取微信用户信息
 */
export async function getUserProfile(): Promise<WechatMiniprogram.UserInfo> {
  return new Promise((resolve, reject) => {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        resolve(res.userInfo)
      },
      fail: (err) => {
        console.error('获取用户信息失败:', err)
        reject(err)
      }
    })
  })
}

/**
 * 微信登录
 */
export async function wxLogin(): Promise<WechatMiniprogram.LoginSuccessCallbackResult> {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => {
        resolve(res)
      },
      fail: (err) => {
        console.error('微信登录失败:', err)
        reject(err)
      }
    })
  })
}

/**
 * 检查用户是否已登录
 */
export function isUserLoggedIn(): boolean {
  const session = wx.getStorageSync('session')
  return session && session.expires_at > Date.now()
}

/**
 * 保存用户会话
 */
export function saveUserSession(session: any) {
  wx.setStorageSync('session', session)
}

/**
 * 清除用户会话
 */
export function clearUserSession() {
  wx.removeStorageSync('session')
  wx.removeStorageSync('userInfo')
}

/**
 * 获取用户OpenID
 */
export function getUserOpenid(): string | undefined {
  const session = wx.getStorageSync('session')
  return session?.openid
}

/**
 * 绑定ERP账号
 */
export async function bindErpAccount(erpUsername: string, erpPassword: string): Promise<any> {
  const openid = getUserOpenid()
  if (!openid) {
    throw new Error('用户未登录')
  }

  return new Promise((resolve, reject) => {
    request({
      url: `${getApp<IAppOption>().globalData.apiBaseUrl}/api/auth/erp-bind`,
      method: 'POST',
      data: {
        openid,
        erpUsername,
        erpPassword
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          resolve(res.data)
        } else {
          reject(new Error(res.data?.message || '绑定失败'))
        }
      },
      fail: (err) => {
        console.error('ERP绑定失败:', err)
        reject(err)
      }
    })
  })
}

/**
 * 获取用户绑定信息
 */
export async function getUserBindingInfo(): Promise<any> {
  const openid = getUserOpenid()
  if (!openid) {
    throw new Error('用户未登录')
  }

  return new Promise((resolve, reject) => {
    request({
      url: `${getApp<IAppOption>().globalData.apiBaseUrl}/api/user/profile`,
      method: 'GET',
      data: { openid },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          resolve(res.data)
        } else {
          reject(new Error('获取用户信息失败'))
        }
      },
      fail: (err) => {
        console.error('获取用户信息失败:', err)
        reject(err)
      }
    })
  })
}