import { orderAPI } from '../../utils/api'
import { showToast } from '../../utils/util'

interface OrderItem {
  orderId: string
  orderNo: string
  customerName: string
  orderDate: string
  statusText: string
  progress: number
}

Page({
  data: {
    searchKeyword: '',
    currentStatus: 'all',
    orderList: [] as OrderItem[],
    isLoading: false,
    isRefreshing: false,
    isLoadingMore: false,
    loadingText: '',
    currentPage: 1,
    pageSize: 10,
    hasMore: true
  },

  onLoad() {
    const sessionId = wx.getStorageSync('sessionId')
    if (!sessionId) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.loadOrders()
  },

  onShow() {
    if (this.data.orderList.length === 0) {
      this.loadOrders()
    }
  },

  onSearchInput(e: any) {
    this.setData({ searchKeyword: e.detail.value })
  },

  onSearch() {
    this.setData({ currentPage: 1, orderList: [], hasMore: true })
    this.loadOrders()
  },

  onStatusFilter(e: any) {
    const status = e.currentTarget.dataset.status
    if (status === this.data.currentStatus) return
    this.setData({ currentStatus: status, currentPage: 1, orderList: [], hasMore: true })
    this.loadOrders()
  },

  onRefresh() {
    this.setData({ isRefreshing: true, currentPage: 1, orderList: [], hasMore: true })
    this.loadOrders()
  },

  onLoadMore() {
    if (this.data.isLoadingMore || !this.data.hasMore) return
    this.setData({ isLoadingMore: true, currentPage: this.data.currentPage + 1 })
    this.loadOrders(true)
  },

  onOrderClick(e: any) {
    const order = e.currentTarget.dataset.order
    wx.navigateTo({ url: `/pages/order-detail/order-detail?orderId=${order.orderId}` })
  },

  async loadOrders(isLoadMore = false) {
    if (this.data.isLoading) return
    this.setData({
      isLoading: !isLoadMore && !this.data.isRefreshing,
      loadingText: isLoadMore ? '加载更多...' : '加载中...'
    })
    try {
      const result = await orderAPI.searchOrders({
        keyword: this.data.searchKeyword,
        status: this.data.currentStatus === 'all' ? undefined : this.data.currentStatus,
        page: this.data.currentPage,
        pageSize: this.data.pageSize
      })
      if (result.success) {
        const orders = (result.data.orders || []).map((order: any) => ({
          orderId: order.order_id,
          orderNo: order.order_no,
          customerName: order.customer_name,
          orderDate: this.formatDate(order.order_date),
          statusText: this.getOrderStatusText(order.status),
          progress: this.calculateProgress(order.materials || [])
        }))
        const newList = isLoadMore ? [...this.data.orderList, ...orders] : orders
        this.setData({
          orderList: newList,
          hasMore: result.data.hasMore,
          isLoading: false,
          isLoadingMore: false,
          isRefreshing: false
        })
        if (orders.length === 0 && !isLoadMore) {
          showToast('暂无相关订单')
        }
      } else {
        if ((result as any).code === 'NEED_INVITE_BIND') {
          showToast('请先绑定企业')
          wx.switchTab({ url: '/pages/index/index' })
          return
        }
        throw new Error(result.message || '加载订单失败')
      }
    } catch (err: any) {
      console.error('Load orders failed:', err)
      this.setData({ isLoading: false, isLoadingMore: false, isRefreshing: false })
      showToast(err?.message || '加载订单失败，请重试')
    }
  },

  getOrderStatusText(status: string): string {
    const map: { [key: string]: string } = {
      pending: '待生产',
      producing: '生产中',
      shipped: '已发货',
      completed: '已完成',
      cancelled: '已取消'
    }
    return map[status] || '待生产'
  },

  calculateProgress(materials: any[]): number {
    if (!materials || materials.length === 0) return 0
    const completed = materials.filter(m => m.status === 'completed').length
    return Math.round((completed / materials.length) * 100)
  },

  formatDate(dateString: string): string {
    const date = new Date(dateString)
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
})
