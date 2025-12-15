import { getWechatLoginCode, request } from '../../utils/api';
import { showToast, showLoading, hideLoading } from '../../utils/util';

Page({
  data: {
    isLoading: false,
    loadingText: '',
    showErpBind: false,
    inviteCode: ''
  },

  async onLoad() {
    // 检查是否已经登录
    const session = wx.getStorageSync('session');
    if (session && session.expires_at > Date.now()) {
        // session 有效，尝试跳转主页
        wx.switchTab({
            url: '/pages/index/index'
        });
    } else {
        // 清除无效 session
        wx.removeStorageSync('session');
        wx.removeStorageSync('sessionId');
    }
  },

  async onGetPhoneNumber(e: any) {
    if (e.detail.errMsg === 'getPhoneNumber:ok') {
      try {
        showLoading('正在登录...');
        
        // 获取微信登录code
        const loginCode = await getWechatLoginCode();
        
        // 模拟获取用户信息（实际场景可结合 getUserProfile 或直接使用手机号信息）
        // 这里为了对齐后端接口要求 userInfo 字段，构造一个基础对象
        // 注意：新版小程序获取头像昵称需单独授权，这里仅作演示或按需调整
        const userInfo = {
            nickName: '微信用户',
            avatarUrl: ''
        };

        // 发送到后端进行登录
        const result = await request({
          url: '/api/auth/wx-login',
          method: 'POST',
          data: {
            code: loginCode,
            userInfo: userInfo
          }
        });
        
        if (result.success) {
          // 保存session信息
          wx.setStorageSync('session', {
            ...result.data,
            expires_at: result.data.expiresAt
          });
          wx.setStorageSync('sessionId', result.data.sessionKey); // 兼容旧逻辑，建议逐步迁移到 session 对象
          
          // 检查是否需要绑定ERP
          // 根据后端返回数据结构判断，或者先尝试获取用户信息来判断绑定状态
          try {
             const profileRes = await request({
                 url: '/api/user/profile',
                 method: 'GET',
                 data: {}
             });
             
            if (profileRes.success) {
                const binding = profileRes.data.erpBinding;
                if (!binding || !binding.companyId) {
                this.setData({
                 showErpBind: true,
                  isLoading: false
                });
                hideLoading();
                return;
                }
            }
          } catch (err) {
              console.warn('Check profile failed', err);
          }

          // 直接跳转到主页
          hideLoading();
          wx.switchTab({
            url: '/pages/index/index'
          });

        } else {
          hideLoading();
          showToast(result.message || '登录失败，请重试');
        }
      } catch (error: any) {
        hideLoading();
        console.error('Login failed:', error);
        showToast(error?.message || '登录失败，请检查网络连接');
      }
    } else {
      showToast('需要授权手机号才能继续使用');
    }
  },

  onInviteCodeInput(e: any) {
    this.setData({
      inviteCode: e.detail.value
    });
  },

  async onBindCompany() {
    const { inviteCode } = this.data;
    if (!inviteCode || !inviteCode.trim()) {
      showToast('请输入微信邀请码');
      return;
    }
    try {
      showLoading('正在绑定...');
      const result = await request({
        url: '/api/auth/bind-company',
        method: 'POST',
        data: {
          inviteCode: inviteCode.trim()
        }
      });
      if (result.success) {
        hideLoading();
        showToast('绑定成功', 'success');
        this.setData({
          showErpBind: false
        });
        setTimeout(() => {
          wx.switchTab({
            url: '/pages/index/index'
          });
        }, 800);
      } else {
        hideLoading();
        showToast(result.message || '绑定失败，请检查邀请码');
      }
    } catch (error) {
      hideLoading();
      console.error('Company bind failed:', error);
      showToast('绑定失败，请检查网络连接');
    }
  },

  onCloseErpBind() {
    this.setData({
      showErpBind: false
    });
  },

  onPrivacyTap() {
    wx.navigateTo({
      url: '/pages/privacy/privacy'
    });
  },

  onTermsTap() {
    wx.navigateTo({
      url: '/pages/terms/terms'
    });
  }
});
