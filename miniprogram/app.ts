import { getUserProfile } from './utils/user'

export interface IAppOption {
  globalData: {
    userInfo?: WechatMiniprogram.UserInfo,
    openid?: string,
    sessionKey?: string,
    apiBaseUrl: string,
    erpStatus: {
      isConnected: boolean,
      lastCheckTime: string,
      responseTime: number
    }
  }
}

App<IAppOption>({
  globalData: {
    userInfo: undefined,
    openid: undefined,
    sessionKey: undefined,
    apiBaseUrl: 'http://localhost:5000', // 需要替换为实际的API域名
    erpStatus: {
      isConnected: true,
      lastCheckTime: '',
      responseTime: 0
    }
  },

  onLaunch() {
    console.log('惠采订单信息查询平台小程序启动')
    
    // 检查更新
    this.checkForUpdate()
    
    // 初始化用户会话
    this.initUserSession()
    
    // 检查ERP接口状态 (已废弃)
    // this.checkErpStatus()
    
    // 设置定时检查ERP状态 (已废弃)
    /*
    setInterval(() => {
      this.checkErpStatus()
    }, 30000) 
    */
  },

  // 检查小程序更新
  checkForUpdate() {
    const updateManager = wx.getUpdateManager()
    
    updateManager.onCheckForUpdate((res) => {
      console.log('检查更新结果:', res.hasUpdate)
    })

    updateManager.onUpdateReady(() => {
      wx.showModal({
        title: '更新提示',
        content: '新版本已经准备好，是否重启应用？',
        success: (res) => {
          if (res.confirm) {
            updateManager.applyUpdate()
          }
        }
      })
    })

    updateManager.onUpdateFailed(() => {
      wx.showToast({
        title: '新版本下载失败',
        icon: 'error'
      })
    })
  },

  // 初始化用户会话
  async initUserSession() {
    try {
      const session = wx.getStorageSync('session')
      if (session && session.expires_at > Date.now()) {
        this.globalData.openid = session.openid
        this.globalData.sessionKey = session.session_key
        
        // 尝试静默登录：检查 session 是否即将过期（如小于1天），如果是则自动刷新 token
        // 这里简单实现：如果 token 存在，就认为已登录；更完善的做法是调用后端 verify_token 接口
        // 获取用户信息
        // const userInfo = await getUserProfile() // getUserProfile 无法静默调用
        // this.globalData.userInfo = userInfo
      } else {
          // session 不存在或过期，尝试静默登录
          this.silentLogin()
      }
    } catch (error) {
      console.error('初始化用户会话失败:', error)
    }
  },

  async silentLogin() {
      // 真正的静默登录：wx.login 获取 code -> 后端换取 openid/token
      // 注意：静默登录无法获取用户头像昵称和手机号
      try {
        const { getWechatLoginCode, request } = require('./utils/api') // 延迟导入避免循环依赖
        const code = await getWechatLoginCode()
        const result = await request({
            url: '/api/auth/wx-login',
            method: 'POST',
            data: { code, userInfo: {} } // 传空 userInfo
        })
        
        if (result.success) {
            wx.setStorageSync('session', {
                ...result.data,
                expires_at: result.data.expiresAt
            })
            this.globalData.openid = result.data.openid
            // 静默登录成功，通知页面或刷新状态
        }
      } catch (err) {
          console.log('静默登录失败，等待用户手动登录', err)
      }
  },

  // 检查ERP接口状态 (已废弃，保留空函数以防其他地方调用)
  async checkErpStatus() {
    // 接口已移除，不再执行检查
    return;
    /*
    try {
      const res = await wx.request({
        url: `${this.globalData.apiBaseUrl}/api/health/check`,
        method: 'GET',
        timeout: 5000
      })
      
      if (res.statusCode === 200 && res.data) {
        this.globalData.erpStatus = {
          isConnected: res.data.status === 'healthy',
          lastCheckTime: new Date().toLocaleString(),
          responseTime: res.data.responseTime || 0
        }
      }
    } catch (error) {
      console.error('检查ERP状态失败:', error)
      this.globalData.erpStatus = {
        isConnected: false,
        lastCheckTime: new Date().toLocaleString(),
        responseTime: 0
      }
    }
    */
  },

  // 全局错误处理
  onError(msg: string) {
    console.error('小程序错误:', msg)
    
    // 记录错误日志
    wx.request({
      url: `${this.globalData.apiBaseUrl}/api/logs/error`,
      method: 'POST',
      data: {
        error: msg,
        timestamp: Date.now(),
        openid: this.globalData.openid
      }
    }).catch(err => {
      console.error('记录错误日志失败:', err)
    })
  },

  // 页面未找到处理
  onPageNotFound(res: any) {
    console.error('页面未找到:', res.path)
    wx.redirectTo({
      url: '/pages/index/index'
    })
  }
})