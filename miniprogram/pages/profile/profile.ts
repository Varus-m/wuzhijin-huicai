import { showToast, showModal, formatDate } from '../../utils/util';
import { request, userAPI } from '../../utils/api';

interface UserInfo {
  nickName?: string;
  avatarUrl?: string;
  phoneNumber?: string;
}

interface EnterpriseInfo {
  code: string;
  name: string;
  customerId: string;
  bindTime: string;
}

interface NotificationSettings {
  orderStatus: boolean;
  productionProgress: boolean;
  shipping: boolean;
  systemMaintenance: boolean;
  importantAnnouncements: boolean;
}

Page({
  data: {
    userInfo: {} as UserInfo,
    isErpBound: false,
    enterpriseInfo: {} as EnterpriseInfo,
    notificationSettings: {
      orderStatus: true,
      productionProgress: true,
      shipping: true,
      systemMaintenance: true,
      importantAnnouncements: true
    } as NotificationSettings,
    
    showEditModal: false,
    showNotificationModal: false,
    editForm: {
      inviteCode: ''
    }
  },

  onLoad() {
    // 检查登录状态
    const session = wx.getStorageSync('session');
    if (!session || !session.token) {
      wx.reLaunch({
        url: '/pages/login/login'
      });
      return;
    }
    
    this.loadUserInfo();
    this.loadNotificationSettings();
    // 首次加载也检查绑定状态并更新信息
    this.checkBindingAndPrompt();
  },

  onShow() {
    // 页面显示时刷新数据
    this.loadUserInfo();
    this.checkBindingAndPrompt();
  },

  // 查询用户绑定状态，未绑定则弹出邀请码绑定弹窗，已绑定则更新信息
  async checkBindingAndPrompt() {
    try {
      const profile = await userAPI.getProfile('');
      if (profile.success) {
        const binding = profile.data?.erpBinding;
        
        // 如果有绑定信息，更新页面展示
        if (binding && binding.companyId) {
          const newEnterpriseInfo = {
            code: binding.companyId || '',
            name: binding.companyName || '',
            customerId: binding.customerId || '',
            bindTime: binding.bindTime || new Date().toISOString() // 后端如果没有返回bindTime，暂时用当前时间
          };
          
          // 更新 Storage，以便下次快速加载
          wx.setStorageSync('enterpriseInfo', newEnterpriseInfo);
          
          this.setData({
            isErpBound: true,
            enterpriseInfo: {
              code: newEnterpriseInfo.code,
              name: newEnterpriseInfo.name,
              customerId: newEnterpriseInfo.customerId,
              bindTime: formatDate(new Date(newEnterpriseInfo.bindTime))
            },
            showEditModal: false // 确保弹窗关闭
          });
        } else {
          // 未绑定，且不是 NEED_INVITE_BIND 状态（正常未绑定），也可能需要提示
          // 但这里主要依靠 code === 'NEED_INVITE_BIND' 来判断是否强制弹窗
          // 如果只是普通未绑定，保持 isErpBound 为 false
          this.setData({
             isErpBound: false,
             enterpriseInfo: {} as EnterpriseInfo
          });
          
          // 如果业务逻辑要求强制绑定，可以在这里弹窗，目前保留原逻辑
          if (!binding) {
              // 可以在这里决定是否自动弹出绑定窗口，或者只显示未绑定状态让用户点击
              // this.setData({ showEditModal: true }); 
          }
        }
      } else if ((profile as any).code === 'NEED_INVITE_BIND') {
        this.setData({
            isErpBound: false,
            showEditModal: true,
            editForm: { inviteCode: '' }
        });
      }
    } catch (err) {
      // 忽略错误，保持页面可用
      console.warn('Check binding failed', err);
    }
  },

  // 加载用户信息
  async loadUserInfo() {
    try {
      const userInfo = wx.getStorageSync('userInfo') || {};
      const enterpriseInfo = wx.getStorageSync('enterpriseInfo') || {};
      
      this.setData({
        userInfo: {
          nickName: userInfo.nickName || '',
          avatarUrl: userInfo.avatarUrl || '',
          phoneNumber: userInfo.phoneNumber || ''
        },
        // 初始加载时先用本地缓存的数据，避免闪烁
        isErpBound: !!enterpriseInfo.code,
        enterpriseInfo: {
          code: enterpriseInfo.code || '',
          name: enterpriseInfo.name || '',
          customerId: enterpriseInfo.customerId || '',
          bindTime: enterpriseInfo.bindTime ? formatDate(new Date(enterpriseInfo.bindTime)) : ''
        }
      });
    } catch (error) {
      console.error('Load user info failed:', error);
      showToast('加载用户信息失败');
    }
  },

  // 加载通知设置
  async loadNotificationSettings() {
    try {
      const settings = wx.getStorageSync('notificationSettings');
      if (settings) {
        this.setData({
          notificationSettings: settings
        });
      }
    } catch (error) {
      console.error('Load notification settings failed:', error);
    }
  },

  // 编辑企业信息
  onEditEnterprise() {
    this.setData({
      showEditModal: true,
      editForm: {
        inviteCode: ''
      }
    });
  },

  // 关闭编辑弹窗
  onCloseEditModal() {
    this.setData({
      showEditModal: false,
      editForm: {
        inviteCode: ''
      }
    });
  },

  // 邀请码输入
  onInviteCodeInput(e: any) {
    this.setData({
      'editForm.inviteCode': e.detail.value
    });
  },

  // 保存企业信息（通过邀请码绑定）
  async onSaveEnterprise() {
    const { inviteCode } = this.data.editForm;
    if (!inviteCode || !inviteCode.trim()) {
      showToast('请输入微信邀请码');
      return;
    }
    try {
      const bindRes = await request({
        url: '/api/auth/bind-company',
        method: 'POST',
        data: { inviteCode: inviteCode.trim() }
      });
      if (bindRes.success) {
        // 绑定成功后拉取最新资料
        const profileRes = await request({
          url: '/api/user/profile',
          method: 'GET',
          data: {}
        });
        if (profileRes.success) {
          const binding = profileRes.data.erpBinding || {};
          const newEnterpriseInfo = {
            code: binding.companyId || '',
            name: binding.companyName || '',
            customerId: binding.customerId || '',
            bindTime: new Date().toISOString()
          };
          wx.setStorageSync('enterpriseInfo', newEnterpriseInfo);
          this.setData({
            isErpBound: !!newEnterpriseInfo.code,
            enterpriseInfo: {
              code: newEnterpriseInfo.code,
              name: newEnterpriseInfo.name,
              customerId: newEnterpriseInfo.customerId,
              bindTime: formatDate(new Date(newEnterpriseInfo.bindTime))
            }
          });
          this.onCloseEditModal();
          showToast('绑定成功', 'success');
        } else {
          showToast('绑定成功，加载资料失败');
        }
      } else {
        showToast(bindRes.message || '绑定失败');
      }
    } catch (error) {
      console.error('Bind enterprise failed:', error);
      showToast('绑定失败，请检查网络连接');
    }
  },

  // 绑定企业
  onBindEnterprise() {
    this.setData({
      showEditModal: true,
      editForm: { inviteCode: '' }
    });
  },

  // 重新绑定企业
  async onRebindEnterprise() {
    const confirmed = await showModal('确认操作', '是否重新绑定企业信息？');
    if (!confirmed) return;
    
    this.onBindEnterprise();
  },

  // 通知设置
  onNotificationSettings() {
    this.setData({
      showNotificationModal: true
    });
  },

  // 关闭通知设置弹窗
  onCloseNotificationModal() {
    this.setData({
      showNotificationModal: false
    });
  },

  // 通知设置变更
  onOrderStatusChange(e: any) {
    this.setData({
      'notificationSettings.orderStatus': e.detail.value
    });
  },

  onProductionProgressChange(e: any) {
    this.setData({
      'notificationSettings.productionProgress': e.detail.value
    });
  },

  onShippingChange(e: any) {
    this.setData({
      'notificationSettings.shipping': e.detail.value
    });
  },

  onSystemMaintenanceChange(e: any) {
    this.setData({
      'notificationSettings.systemMaintenance': e.detail.value
    });
  },

  onImportantAnnouncementsChange(e: any) {
    this.setData({
      'notificationSettings.importantAnnouncements': e.detail.value
    });
  },

  // 保存通知设置
  async onSaveNotificationSettings() {
    try {
      // 保存到本地存储
      wx.setStorageSync('notificationSettings', this.data.notificationSettings);
      
      // 同步到后端
      await this.syncNotificationSettings(this.data.notificationSettings);
      
      this.onCloseNotificationModal();
      showToast('通知设置已保存', 'success');
    } catch (error) {
      console.error('Save notification settings failed:', error);
      showToast('保存失败，请重试');
    }
  },

  // 隐私设置
  onPrivacySettings() {
    wx.navigateTo({
      url: '/pages/privacy-settings/privacy-settings'
    });
  },

  // 关于我们
  onAbout() {
    wx.navigateTo({
      url: '/pages/about/about'
    });
  },

  // 帮助中心
  onHelp() {
    wx.navigateTo({
      url: '/pages/help/help'
    });
  },

  // 退出登录
  async onLogout() {
    const confirmed = await showModal('确认退出', '是否确认退出登录？');
    if (!confirmed) return;
    
    try {
      // 清除本地存储
      wx.removeStorageSync('session');
      wx.removeStorageSync('userInfo');
      wx.removeStorageSync('enterpriseInfo');
      wx.removeStorageSync('notificationSettings');
      
      // 跳转到登录页
      wx.reLaunch({
        url: '/pages/login/login'
      });
    } catch (error) {
      console.error('Logout failed:', error);
      showToast('退出失败，请重试');
    }
  },

  // 同步通知设置API调用
  async syncNotificationSettings(settings: NotificationSettings) {
    // 实际项目中应调用后端API
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(true);
      }, 500);
    });
  }
});