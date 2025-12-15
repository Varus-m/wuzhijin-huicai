import { orderAPI } from '../../utils/api'
import { showToast } from '../../utils/util'

interface MaterialItem {
  materialId: string
  code: string
  statusText: string
}

Page({
  data: {
    orderId: '',
    orderNo: '',
    customerName: '',
    orderDate: '',
    statusText: '',
    progress: 0,
    materials: [] as MaterialItem[],
    isLoading: false
  },

  onLoad(options: any) {
    const { orderId } = options || {}
    if (!orderId) {
      showToast('缺少订单ID')
      return
    }
    this.setData({ orderId })
    this.loadDetail()
  },

  async loadDetail() {
    this.setData({ isLoading: true })
    try {
      const [detail, materialsRes] = await Promise.all([
        orderAPI.getOrderDetail(this.data.orderId),
        orderAPI.getOrderMaterials(this.data.orderId)
      ])
      if (!detail.success || !materialsRes.success) {
        if ((detail as any).code === 'NEED_INVITE_BIND' || (materialsRes as any).code === 'NEED_INVITE_BIND') {
          showToast('请先绑定企业')
          wx.switchTab({ url: '/pages/index/index' })
          return
        }
        throw new Error(detail.message || materialsRes.message || '加载订单详情失败')
      }
      const d = detail.data
      this.setData({
        orderNo: d.order_no,
        customerName: d.customer_name,
        orderDate: this.formatDate(d.order_date),
        statusText: this.getOrderStatusText(d.status),
        progress: this.calculateProgress((materialsRes && materialsRes.data && materialsRes.data.materials) ? materialsRes.data.materials : [])
      })

      const materialsSource = (materialsRes && materialsRes.data && materialsRes.data.materials) ? materialsRes.data.materials : []
      const materials = materialsSource.map((m: any) => ({
        materialId: m.material_id,
        code: m.material_code,
        statusText: this.getMaterialStatusText(m.status)
      }))
      this.setData({ materials })
    } catch (err: any) {
      console.error('Load order detail failed:', err)
      showToast(err?.message || '加载订单详情失败')
    } finally {
      this.setData({ isLoading: false })
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

  getMaterialStatusText(status: string): string {
    const map: { [key: string]: string } = {
      pending: '待生产',
      producing: '生产中',
      completed: '已完成',
      quality_check: '质检中'
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
