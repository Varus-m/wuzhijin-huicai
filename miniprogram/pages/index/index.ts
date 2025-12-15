import { orderAPI, userAPI } from '../../utils/api';
import { showToast, showLoading, hideLoading } from '../../utils/util';

interface OrderItem {
  orderId: string;
  orderNo: string;
  customerName: string;
  orderDate: string;
  status: string;
  statusText: string;
  materialCount: number;
  materials: MaterialItem[];
  progress: number;
}

interface MaterialItem {
  materialId: string;
  code: string;
  status: string;
  statusText: string;
}

Page({
  data: {
    searchKeyword: '',
    currentStatus: 'all',
    orderList: [] as OrderItem[],
    isLoading: false,
    isLoadingMore: false,
    isRefreshing: false,
    loadingText: '',
    currentPage: 1,
    pageSize: 10,
    hasMore: true,
    showBindCompany: false,
    inviteCode: ''
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
  },

  async onShow() {
    // 页面显示时刷新数据
    const isBound = await this.checkUserBinding();
    
    if (isBound && this.data.orderList.length === 0) {
      this.loadOrders();
    }
  },

  // 检查用户绑定状态
   async checkUserBinding(): Promise<boolean> {
     try {
       const session = wx.getStorageSync('session') || {}
       if (!session?.token) return false;

       const profile = await userAPI.getProfile('');
       if (profile.success) {
          const binding = profile.data.erpBinding;
          if (!binding || !binding.companyId) {
              this.setData({ showBindCompany: true });
              return false;
          }
          return true;
       } else if (profile.code === 'NEED_INVITE_BIND') {
          this.setData({ showBindCompany: true });
          return false;
       }
       return false;
     } catch (err) {
       console.error('Check binding status failed', err);
       return false;
     }
   },

   onInviteCodeInput(e: any) {
     this.setData({ inviteCode: e.detail.value });
   },

   async onBindCompanyTap() {
     const code = (this.data.inviteCode || '').trim();
     if (!code) {
       showToast('邀请码不能为空');
       return;
     }
     try {
       showLoading('绑定中...');
       const result = await userAPI.bindCompany(code);
       hideLoading();
       if (result.success) {
         showToast('绑定成功');
         this.setData({ showBindCompany: false, inviteCode: '' });
         this.setData({ currentPage: 1, orderList: [], hasMore: true });
         this.loadOrders();
       } else {
         showToast(result.message || '绑定失败');
       }
     } catch (error: any) {
       hideLoading();
       showToast(error.message || '绑定异常');
     }
   },

   onCloseBindCompany() {
     // 若必须强制绑定，可不提供关闭入口；此处保留关闭按钮，用户可返回登录页
     this.setData({ showBindCompany: false });
   },

  // 执行搜索
  onSearch() {
    this.setData({
      currentPage: 1,
      orderList: [],
      hasMore: true
    });
    this.loadOrders();
  },

  // 状态筛选
  onStatusFilter(e: any) {
    const status = e.currentTarget.dataset.status;
    if (status === this.data.currentStatus) return;
    
    this.setData({
      currentStatus: status,
      currentPage: 1,
      orderList: [],
      hasMore: true
    });
    this.loadOrders();
  },

  // 下拉刷新
  onRefresh() {
    this.setData({
      isRefreshing: true,
      currentPage: 1,
      orderList: [],
      hasMore: true
    });
    this.loadOrders();
  },

  // 加载更多
  onLoadMore() {
    if (this.data.isLoadingMore || !this.data.hasMore) return;
    
    this.setData({
      isLoadingMore: true,
      currentPage: this.data.currentPage + 1
    });
    this.loadOrders(true);
  },

  // 扫码查询
  onScanCode() {
    wx.scanCode({
      success: (res) => {
        const result = res.result;
        if (result) {
          this.setData({
            searchKeyword: result,
            currentPage: 1,
            orderList: [],
            hasMore: true
          });
          this.loadOrders();
        }
      },
      fail: () => {
        showToast('扫码失败，请重试');
      }
    });
  },

  // 订单点击
  onOrderClick(e: any) {
    const order = e.currentTarget.dataset.order;
    wx.navigateTo({
      url: `/pages/order-detail/order-detail?orderId=${order.orderId}`
    });
  },

  // 加载订单数据
  async loadOrders(isLoadMore = false) {
    if (this.data.isLoading) return;
    
    this.setData({
      isLoading: !isLoadMore && !this.data.isRefreshing,
      loadingText: isLoadMore ? '加载更多...' : '加载中...'
    });
    
    try {
      const result = await orderAPI.searchOrders({
        keyword: this.data.searchKeyword,
        status: this.data.currentStatus === 'all' ? undefined : this.data.currentStatus,
        page: this.data.currentPage,
        pageSize: this.data.pageSize
      });
      
      if (result.success) {
        const orders = this.formatOrders(result.data.orders);
        const newOrderList = isLoadMore 
          ? [...this.data.orderList, ...orders]
          : orders;
        
        this.setData({
          orderList: newOrderList,
          hasMore: result.data.hasMore,
          isLoading: false,
          isLoadingMore: false,
          isRefreshing: false
        });
        
        if (orders.length === 0 && !isLoadMore) {
          showToast('暂无相关订单');
        }
      } else {
        if ((result as any).code === 'NEED_INVITE_BIND') {
            this.setData({ showBindCompany: true });
            this.setData({
              isLoading: false,
              isLoadingMore: false,
              isRefreshing: false
            });
            return;
        }
        throw new Error(result.message || '加载订单失败');
      }
    } catch (error: any) {
      console.error('Load orders failed:', error);
      this.setData({
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false
      });
      const msg = error?.message || '加载订单失败，请重试'
      showToast(msg)
      if (msg.includes('未绑定企业') || error?.code === 'NEED_INVITE_BIND') {
        this.setData({ showBindCompany: true })
      }
    }
  },

  // 格式化订单数据
  formatOrders(orders: any[]): OrderItem[] {
    return orders.map(order => ({
      orderId: order.order_id,
      orderNo: order.order_no,
      customerName: order.customer_name,
      orderDate: this.formatDate(order.order_date),
      status: this.getOrderStatus(order.status),
      statusText: this.getOrderStatusText(order.status),
      materialCount: order.material_count || 0,
      materials: this.formatMaterials(order.materials || []),
      progress: this.calculateProgress(order.materials || [])
    }));
  },

  // 格式化物料数据
  formatMaterials(materials: any[]): MaterialItem[] {
    return materials.slice(0, 5).map(material => ({
      materialId: material.material_id,
      code: material.material_code,
      status: this.getMaterialStatus(material.status),
      statusText: this.getMaterialStatusText(material.status)
    }));
  },

  // 获取订单状态
  getOrderStatus(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'pending',
      'producing': 'producing',
      'shipped': 'shipped',
      'completed': 'completed',
      'cancelled': 'cancelled'
    };
    return statusMap[status] || 'pending';
  },

  // 获取订单状态文本
  getOrderStatusText(status: string): string {
    const statusTextMap: { [key: string]: string } = {
      'pending': '待生产',
      'producing': '生产中',
      'shipped': '已发货',
      'completed': '已完成',
      'cancelled': '已取消'
    };
    return statusTextMap[status] || '待生产';
  },

  // 获取物料状态
  getMaterialStatus(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'pending',
      'producing': 'producing',
      'completed': 'completed',
      'quality_check': 'producing'
    };
    return statusMap[status] || 'pending';
  },

  // 获取物料状态文本
  getMaterialStatusText(status: string): string {
    const statusTextMap: { [key: string]: string } = {
      'pending': '待生产',
      'producing': '生产中',
      'completed': '已完成',
      'quality_check': '质检中'
    };
    return statusTextMap[status] || '待生产';
  },

  // 计算订单进度
  calculateProgress(materials: any[]): number {
    if (!materials || materials.length === 0) return 0;
    
    const completedCount = materials.filter(m => m.status === 'completed').length;
    return Math.round((completedCount / materials.length) * 100);
  },

  // 格式化日期 
  formatDate(dateString: string): string { 
    const date = new Date(dateString); 
    const now = new Date(); 
    
    // 清除时分秒，只比较日期
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const targetDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    
    const diffTime = today.getTime() - targetDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)); 
    
    if (diffDays === 0) { 
      return '今天'; 
    } else if (diffDays === 1) { 
      return '昨天'; 
    } else if (diffDays > 1 && diffDays <= 7) { 
      return `${diffDays}天前`; 
    } else { 
      return `${date.getMonth() + 1}月${date.getDate()}日`; 
    } 
  }
});
