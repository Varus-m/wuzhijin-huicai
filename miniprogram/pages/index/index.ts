import { orderAPI, userAPI } from '../../utils/api';
import { showToast, showLoading, hideLoading } from '../../utils/util';

interface OrderItem {
  orderId: string;
  orderNo: string;
  customerName: string;
  orderDate: string;
  status: string;
  statusText: string;
  rmbAmount: string;
  deliveryDate: string;
  deliveryStatus: number;
  deliveryStatusText: string;
  remark: string;
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

interface OrderGroup {
  id: string;
  title: string;
  count: number;
  isExpanded: boolean;
  orders: OrderItem[];
}

Page({
  data: {
    searchKeyword: '',
    currentStatus: 'all',
    orderList: [] as OrderItem[],
    orderGroups: [] as OrderGroup[],
    activeGroupId: 'shipped', // 当前激活的左侧菜单项
    isLoading: false,
    isLoadingMore: false,
    isRefreshing: false,
    loadingText: '',
    currentPage: 1,
    // pageSize: 10, // 默认不分页（查询全部）
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

  // 页面下拉刷新
  onPullDownRefresh() {
    this.onRefresh();
  },

  // 页面上拉触底
  onReachBottom() {
    this.onLoadMore();
  },

  // 刷新逻辑
  onRefresh() {
    this.setData({
      isRefreshing: true,
      currentPage: 1,
      orderList: [],
      hasMore: true
    });
    this.loadOrders();
  },

  // 加载更多逻辑
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
        page: this.data.currentPage
        // pageSize: 10
      });
      
      // 停止下拉刷新动画
      if (this.data.isRefreshing) {
        wx.stopPullDownRefresh();
      }

      if (result.success) {
        const orders = this.formatOrders(result.data.orders);
        const newOrderList = isLoadMore 
          ? [...this.data.orderList, ...orders]
          : orders;
        
        // 分组处理
        const groups = this.groupOrders(newOrderList);

        this.setData({
          orderList: newOrderList,
          orderGroups: groups,
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
      
      if (this.data.isRefreshing) {
        wx.stopPullDownRefresh();
      }

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

  // 对订单进行分组
  groupOrders(orders: OrderItem[]): OrderGroup[] {
    const groups: OrderGroup[] = [
      { id: 'shipped', title: '已发货', count: 0, isExpanded: true, orders: [] },
      { id: 'partial', title: '部分发货', count: 0, isExpanded: true, orders: [] },
      { id: 'unshipped', title: '未发货', count: 0, isExpanded: true, orders: [] },
      { id: 'completed', title: '已完成', count: 0, isExpanded: false, orders: [] }
    ];

    orders.forEach(order => {
      // 判断归属组
      // 优先级：已完成 > 已发货 > 部分发货 > 未发货
      // 注意：deliveryStatus: 0:未发货, 1:已发货, 2:部分发货
      
      let groupId = 'unshipped';
      
      // 如果状态是已完成 (status: 4 或 completed)，则归为已完成
      if (order.status === '4' || order.statusText === '已完成' || order.status === 'completed') {
        groupId = 'completed';
      } else {
        // 根据发货状态分类
        switch (order.deliveryStatus) {
          case 1:
            groupId = 'shipped';
            break;
          case 2:
            groupId = 'partial';
            break;
          case 0:
          default:
            groupId = 'unshipped';
            break;
        }
      }

      const group = groups.find(g => g.id === groupId);
      if (group) {
        group.orders.push(order);
      }
    });

    // 更新计数
    groups.forEach(g => g.count = g.orders.length);

    return groups;
  },

  // 切换分组展开/折叠
  toggleGroup(e: any) {
    const id = e.currentTarget.dataset.id;
    const groups = this.data.orderGroups.map(g => {
      if (g.id === id) {
        return { ...g, isExpanded: !g.isExpanded };
      }
      return g;
    });
    this.setData({ orderGroups: groups });
  },

  // 切换侧边栏菜单
  onMenuClick(e: any) {
    const id = e.currentTarget.dataset.id;
    this.setData({ activeGroupId: id });
    
    // 滚动到对应位置
    // 确保目标分组展开
    const groups = this.data.orderGroups.map(g => {
      if (g.id === id) {
        return { ...g, isExpanded: true };
      }
      return g;
    });
    this.setData({ orderGroups: groups });

    // 先清空再设置，确保触发滚动（某些情况下 id 没变可能不触发，虽然这里 id 变了）
    this.setData({ scrollIntoViewId: '' }, () => {
       this.setData({ scrollIntoViewId: `group-${id}` });
    });
  },

  // 格式化订单数据
  formatOrders(orders: any[]): OrderItem[] {
    return orders.map(order => ({
      orderId: order.order_id,
      orderNo: order.order_no,
      customerName: order.customer_name,
      orderDate: this.formatDate(order.order_date, false), // 下单日期只显示日期
      status: this.getOrderStatus(order.status),
      statusText: this.getOrderStatusText(order.status),
      rmbAmount: order.rmb_amount ? `¥${Number(order.rmb_amount).toFixed(2)}` : '¥0.00',
      deliveryDate: order.delivery_date ? this.formatDate(order.delivery_date, true) : '-', // 交货日期显示相对时间
      shippedRate: order.shipped_rate ? Math.round(order.shipped_rate * 100) : 0,
      deliveryStatus: order.delivery_status || 0,
      deliveryStatusText: this.getDeliveryStatusText(order.delivery_status),
      remark: order.remark || '',
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

  // 获取发货状态文本
  getDeliveryStatusText(status: number): string {
    const statusMap: { [key: number]: string } = {
      0: '未发货',
      1: '已发货',
      2: '部分发货'
    };
    return statusMap[status] || '未发货';
  },

  // 获取订单状态
  getOrderStatus(status: string | number): string {
    const statusMap: { [key: string]: string } = {
      '2': 'producing', // 暂时映射为 producing 样式
      '4': 'completed',
      'pending': 'pending',
      'producing': 'producing',
      'shipped': 'shipped',
      'completed': 'completed',
      'cancelled': 'cancelled'
    };
    return statusMap[String(status)] || 'pending';
  },

  // 获取订单状态文本
  getOrderStatusText(status: string | number): string {
    const statusTextMap: { [key: string]: string } = {
      '2': '已下单',
      '4': '已完成',
      'pending': '待生产',
      'producing': '生产中',
      'shipped': '已发货',
      'completed': '已完成',
      'cancelled': '已取消'
    };
    return statusTextMap[String(status)] || '待生产';
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
  formatDate(dateString: string, showRelative: boolean = false): string { 
    if (!dateString) return '-';
    
    const date = new Date(dateString); 
    const now = new Date(); 
    
    // 基础日期格式: 12月16日
    const basicDate = `${date.getMonth() + 1}月${date.getDate()}日`;
    
    // 如果不需要相对时间，直接返回日期
    if (!showRelative) {
      return basicDate;
    }

    // 清除时分秒，只比较日期
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const targetDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    
    // 计算天数差：目标日期 - 今天
    const diffTime = targetDate.getTime() - today.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)); 
    
    // 只处理今天和未来的日期
    if (diffDays === 0) { 
      return `${basicDate} (今天)`; 
    } else if (diffDays === 1) { 
      return `${basicDate} (明天)`; 
    } else if (diffDays === 2) {
      return `${basicDate} (后天)`;
    } else if (diffDays > 2) { 
      return `${basicDate} (${diffDays}天后)`; 
    } else { 
      // 过去的日期只显示日期
      return basicDate; 
    } 
  }
});