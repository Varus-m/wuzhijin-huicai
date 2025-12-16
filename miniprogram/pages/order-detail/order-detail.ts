import { orderAPI } from '../../utils/api'
import { showToast } from '../../utils/util'

interface DeliveryProduct {
  productName: string;
  spec: string;
  quantity: number;
}

interface DeliveryOrder {
  deliveryDate: string;
  logisticsCompany: string;
  logisticsCode: string;
  address: string;
  remark: string;
  attachments: string[];
  products: DeliveryProduct[];
}

Page({
  data: {
    orderId: '',
    orderNo: '',
    customerName: '',
    rmbAmount: '',
    orderDate: '',
    statusText: '',
    deliveryOrders: [] as DeliveryOrder[],
    isLoading: false
  },

  onLoad(options: any) {
    // 兼容 orderId 和 orderNo 参数，优先使用 orderNo
    const orderNo = options.orderNo || options.orderId || ''
    
    if (!orderNo) {
      showToast('缺少订单号')
      return
    }
    this.setData({ orderNo: orderNo }) // 这里为了兼容逻辑，暂时可以用 orderNo 覆盖之前的 orderId 逻辑，或者在 data 里新增 orderNo
    this.loadDetail()
  },

  async loadDetail() {
    this.setData({ isLoading: true })
    try {
      const detail = await orderAPI.getOrderDetail(this.data.orderNo)
      
      if (!detail.success) {
        if ((detail as any).code === 'NEED_INVITE_BIND') {
          showToast('请先绑定企业')
          wx.switchTab({ url: '/pages/index/index' })
          return
        }
        throw new Error(detail.message || '加载订单详情失败')
      }
      const d = detail.data
      
      // 格式化发运单数据
      const deliveryOrders = (d.delivery_orders || []).map((doItem: any) => ({
        deliveryDate: this.formatDate(doItem.delivery_date),
        logisticsCompany: doItem.logistics_company || '-',
        logisticsCode: doItem.logistics_code || '', // 默认为空字符串，方便判断
        address: doItem.address || '',
        remark: doItem.remark || '',
        // 清洗附件URL，去除可能的空格和反引号
        attachments: (doItem.attachments || []).map((url: string) => url.replace(/[`\s]/g, '')),
        products: doItem.products || []
      }))

      this.setData({
        orderNo: d.order_no,
        customerName: d.customer_name,
        rmbAmount: this.formatMoney(d.rmb_amount),
        orderDate: this.formatDate(d.created_at || d.order_date),
        statusText: this.getOrderStatusText(d.status),
        deliveryOrders: deliveryOrders
      })
    } catch (err: any) {
      console.error('Load order detail failed:', err)
      showToast(err?.message || '加载订单详情失败')
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 预览图片
  onPreviewImage(e: any) {
    const url = e.currentTarget.dataset.url;
    const urls = e.currentTarget.dataset.urls;
    wx.previewImage({
      current: url,
      urls: urls
    });
  },

  getOrderStatusText(status: string | number): string {
    const map: { [key: string]: string } = {
      '2': '已下单',
      '4': '已完成',
      'pending': '待生产',
      'producing': '生产中',
      'shipped': '已发货',
      'completed': '已完成',
      'cancelled': '已取消'
    }
    return map[String(status)] || '待生产'
  },

  formatDate(dateString: string): string {
    const date = new Date(dateString)
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  },

  formatMoney(amount: any): string {
    if (amount === null || amount === undefined) return '0.00'
    return Number(amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
})
