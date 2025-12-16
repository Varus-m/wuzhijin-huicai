import { messageAPI } from '../../utils/api';
import { showToast, showModal, formatDate } from '../../utils/util';

interface MessageItem {
  messageId: string;
  type: string;
  typeText: string;
  typeIcon: string;
  title: string;
  description: string;
  data?: Array<{key: string, value: string}>;
  footer: string;
  isRead: boolean;
  createTime: string;
  timeText: string;
  action?: {
    type: string;
    text: string;
    url?: string;
    orderId?: string;
    orderNo?: string;
  };
}

Page({
  data: {
    messageList: [] as MessageItem[],
    currentType: 'all',
    unreadCount: 0,
    totalCount: 0,
    todayCount: 0,
    isLoading: false,
    isLoadingMore: false,
    isRefreshing: false,
    loadingText: '',
    currentPage: 1,
    pageSize: 20,
    hasMore: true,
    showMessageDetail: false,
    selectedMessage: null as MessageItem | null
  },

  onLoad() {
    // 检查登录状态
    const sessionId = wx.getStorageSync('sessionId');
    if (!sessionId) {
      wx.reLaunch({
        url: '/pages/login/login'
      });
      return;
    }
    
    this.loadMessages();
  },

  onShow() {
    // 页面显示时刷新数据
    if (this.data.messageList.length === 0) {
      this.loadMessages();
    } else {
      this.updateMessageStats();
    }
  },

  // 消息类型筛选
  onTypeFilter(e: any) {
    const type = e.currentTarget.dataset.type;
    if (type === this.data.currentType) return;
    
    this.setData({
      currentType: type,
      currentPage: 1,
      messageList: [],
      hasMore: true
    });
    this.loadMessages();
  },

  // 标记全部已读
  async onMarkAllRead() {
    if (this.data.unreadCount === 0) {
      showToast('没有未读消息');
      return;
    }

    const confirmed = await showModal('确认操作', '是否标记所有消息为已读？');
    if (!confirmed) return;

    try {
      const result = await messageAPI.markAllRead();
      if (result.success) {
        // 更新本地消息状态
        const updatedList = this.data.messageList.map(msg => ({
          ...msg,
          isRead: true
        }));
        
        this.setData({
          messageList: updatedList,
          unreadCount: 0
        });
        
        showToast('已标记全部已读', 'success');
      } else {
        throw new Error(result.message || '操作失败');
      }
    } catch (error: any) {
      console.error('Mark all read failed:', error);
      showToast(error?.message || '操作失败，请重试');
    }
  },

  // 清空所有消息
  async onClearAll() {
    if (this.data.totalCount === 0) {
      showToast('没有消息可清空');
      return;
    }

    const confirmed = await showModal('确认操作', '是否清空所有消息？此操作不可恢复。');
    if (!confirmed) return;

    try {
      const result = await messageAPI.clearAll();
      if (result.success) {
        this.setData({
          messageList: [],
          unreadCount: 0,
          totalCount: 0,
          todayCount: 0,
          hasMore: false
        });
        
        showToast('已清空所有消息', 'success');
      } else {
        throw new Error(result.message || '操作失败');
      }
    } catch (error: any) {
      console.error('Clear all failed:', error);
      showToast(error?.message || '操作失败，请重试');
    }
  },

  // 下拉刷新
  onRefresh() {
    this.setData({
      isRefreshing: true,
      currentPage: 1,
      messageList: [],
      hasMore: true
    });
    this.loadMessages();
  },

  // 加载更多
  onLoadMore() {
    if (this.data.isLoadingMore || !this.data.hasMore) return;
    
    this.setData({
      isLoadingMore: true,
      currentPage: this.data.currentPage + 1
    });
    this.loadMessages(true);
  },

  // 消息点击
  onMessageClick(e: any) {
    const message = e.currentTarget.dataset.message;
    this.setData({
      selectedMessage: message,
      showMessageDetail: true
    });
    
    // 标记为已读
    if (!message.isRead) {
      this.markAsRead(message.messageId);
    }
  },

  // 关闭消息详情
  onCloseModal() {
    this.setData({
      showMessageDetail: false,
      selectedMessage: null
    });
  },

  // 消息操作
  onMessageAction() {
    const message = this.data.selectedMessage;
    if (!message || !message.action) return;

    const action = message.action;
    
    switch (action.type) {
      case 'navigate':
        // 优先使用 orderNo，如果 action 中有 orderId 但其实是 orderNo 的值，也传给 orderNo 参数
        // 假设 action 对象结构可能包含 orderId 或 orderNo
        const targetOrderNo = action.orderNo || action.orderId;
        if (targetOrderNo) {
          wx.navigateTo({
            url: `/pages/order-detail/order-detail?orderNo=${targetOrderNo}`
          });
        }
        break;
      case 'webview':
        if (action.url) {
          wx.navigateTo({
            url: `/pages/webview/webview?url=${encodeURIComponent(action.url)}`
          });
        }
        break;
      default:
        showToast('暂不支持此操作');
    }
    
    this.onCloseModal();
  },

  // 加载消息数据
  async loadMessages(isLoadMore = false) {
    if (this.data.isLoading) return;
    
    this.setData({
      isLoading: !isLoadMore && !this.data.isRefreshing,
      loadingText: isLoadMore ? '加载更多...' : '加载中...'
    });
    
    try {
      const result = await messageAPI.getMessageHistory(
        this.data.currentPage,
        this.data.pageSize,
        this.data.currentType === 'all' ? undefined : this.data.currentType
      );
      
      if (result.success) {
        const messages = this.formatMessages(result.data.messages);
        const newMessageList = isLoadMore 
          ? [...this.data.messageList, ...messages]
          : messages;
        
        this.setData({
          messageList: newMessageList,
          hasMore: result.data.hasMore,
          isLoading: false,
          isLoadingMore: false,
          isRefreshing: false
        });
        
        this.updateMessageStats();
        
        if (messages.length === 0 && !isLoadMore) {
          showToast('暂无相关消息');
        }
      } else {
        throw new Error(result.message || '加载消息失败');
      }
    } catch (error: any) {
      console.error('Load messages failed:', error);
      this.setData({
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false
      });
      showToast(error?.message || '加载消息失败，请重试');
    }
  },

  // 格式化消息数据
  formatMessages(messages: any[]): MessageItem[] {
    return messages.map(message => {
      const typeInfo = this.getMessageTypeInfo(message.type);
      return {
        messageId: message.message_id,
        type: message.type,
        typeText: typeInfo.text,
        typeIcon: typeInfo.icon,
        title: message.title,
        description: message.description,
        data: this.formatMessageData(message.data),
        footer: message.footer || '点击查看详情',
        isRead: message.is_read,
        createTime: message.create_time,
        timeText: this.formatTimeText(message.create_time),
        action: message.action
      };
    });
  },

  // 获取消息类型信息
  getMessageTypeInfo(type: string) {
    const typeMap: { [key: string]: { text: string, icon: string } } = {
      'order_status': {
        text: '订单状态',
        icon: '/images/icon-order-status.png'
      },
      'shipping': {
        text: '发货通知',
        icon: '/images/icon-shipping.png'
      },
      'production': {
        text: '生产提醒',
        icon: '/images/icon-production.png'
      },
      'system': {
        text: '系统通知',
        icon: '/images/icon-system.png'
      }
    };
    return typeMap[type] || { text: '未知类型', icon: '/images/icon-default.png' };
  },

  // 格式化消息数据
  formatMessageData(data: any): Array<{key: string, value: string}> | undefined {
    if (!data || typeof data !== 'object') return undefined;
    
    return Object.entries(data).map(([key, value]) => ({
      key: this.formatDataKey(key),
      value: String(value)
    }));
  },

  // 格式化数据键名
  formatDataKey(key: string): string {
    const keyMap: { [key: string]: string } = {
      'order_no': '订单号',
      'customer_name': '客户名称',
      'material_code': '物料编码',
      'status': '状态',
      'progress': '进度',
      'shipping_no': '快递单号',
      'estimated_date': '预计时间'
    };
    return keyMap[key] || key;
  },

  // 格式化时间文本
  formatTimeText(timeString: string): string {
    const messageTime = new Date(timeString);
    const now = new Date();
    const diffTime = now.getTime() - messageTime.getTime();
    const diffMinutes = Math.floor(diffTime / (1000 * 60));
    const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffMinutes < 1) {
      return '刚刚';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}分钟前`;
    } else if (diffHours < 24) {
      return `${diffHours}小时前`;
    } else if (diffDays < 7) {
      return `${diffDays}天前`;
    } else {
      return formatDate(messageTime, 'MM-DD HH:mm');
    }
  },

  // 更新消息统计
  updateMessageStats() {
    const messages = this.data.messageList;
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    const unreadCount = messages.filter(msg => !msg.isRead).length;
    const totalCount = messages.length;
    const todayCount = messages.filter(msg => {
      const msgDate = new Date(msg.createTime);
      return msgDate >= today;
    }).length;
    
    this.setData({
      unreadCount,
      totalCount,
      todayCount
    });
  },

  // 标记消息为已读
  async markAsRead(messageId: string) {
    try {
      await messageAPI.markAsRead(messageId);
      
      // 更新本地消息状态
      const updatedList = this.data.messageList.map(msg => 
        msg.messageId === messageId 
          ? { ...msg, isRead: true }
          : msg
      );
      
      this.setData({
        messageList: updatedList
      });
      
      this.updateMessageStats();
    } catch (error) {
      console.error('Mark as read failed:', error);
    }
  }
});
