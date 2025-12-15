import { systemAPI } from '../../utils/api';
import { showToast, formatDate } from '../../utils/util';

interface ErrorLog {
  logId: string;
  time: string;
  level: string;
  levelText: string;
  message: string;
  source: string;
}

interface PerformanceData {
  responseTimeData: number[];
  requestCountData: number[];
  labels: string[];
}

Page({
  data: {
    systemStatus: 'normal',
    systemStatusText: '系统运行正常',
    systemStatusIcon: '/images/icon-system-normal.png',
    lastCheckTime: '',
    
    erpStatus: 'normal',
    erpResponseTime: 0,
    erpSuccessRate: 100,
    erpTodayRequests: 0,
    
    wechatStatus: 'normal',
    wechatResponseTime: 0,
    wechatSuccessRate: 100,
    wechatTodayCalls: 0,
    
    avgResponseTime: 0,
    avgResponseTimeTrend: 'stable',
    avgResponseTimeTrendText: '稳定',
    
    avgSuccessRate: 100,
    avgSuccessRateTrend: 'stable',
    avgSuccessRateTrendText: '稳定',
    
    totalRequests: 0,
    totalRequestsTrend: 'stable',
    totalRequestsTrendText: '稳定',
    
    errorLogs: [] as ErrorLog[],
    performanceData: {} as PerformanceData,
    
    isLoading: false,
    loadingText: '',
    
    refreshTimer: null as NodeJS.Timeout | null
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
    
    this.loadMonitorData();
    this.startAutoRefresh();
  },

  onUnload() {
    // 清理定时器
    if (this.data.refreshTimer) {
      clearInterval(this.data.refreshTimer);
    }
  },

  // 开始自动刷新
  startAutoRefresh() {
    const timer = setInterval(() => {
      this.loadMonitorData();
    }, 30000); // 30秒刷新一次
    
    this.setData({
      refreshTimer: timer
    });
  },

  // 手动刷新
  onRefresh() {
    this.loadMonitorData();
  },

  // 查看所有日志
  onViewAllLogs() {
    wx.navigateTo({
      url: '/pages/logs/logs'
    });
  },

  // 加载监控数据
  async loadMonitorData() {
    if (this.data.isLoading) return;
    
    this.setData({
      isLoading: true,
      loadingText: '加载监控数据中...'
    });
    
    try {
      // 并行获取所有监控数据
      const [healthResult, erpResult, wechatResult, metricsResult] = await Promise.all([
        systemAPI.healthCheck(),
        systemAPI.getErpStatus(),
        systemAPI.getWechatStatus(),
        systemAPI.getPerformanceMetrics()
      ]);
      
      if (healthResult.success && erpResult.success && wechatResult.success && metricsResult.success) {
        this.updateSystemStatus(healthResult.data);
        this.updateErpStatus(erpResult.data);
        this.updateWechatStatus(wechatResult.data);
        this.updatePerformanceMetrics(metricsResult.data);
        
        // 更新最后检查时间
        this.setData({
          lastCheckTime: formatDate(new Date(), 'HH:mm:ss')
        });
        
        // 绘制图表
        this.drawCharts();
      } else {
        throw new Error('获取监控数据失败');
      }
    } catch (error: any) {
      console.error('Load monitor data failed:', error);
      
      // 设置错误状态
      this.setData({
        systemStatus: 'error',
        systemStatusText: '系统连接失败',
        systemStatusIcon: '/images/icon-system-error.png'
      });
      
      showToast(error?.message || '加载监控数据失败，请重试');
    } finally {
      this.setData({
        isLoading: false
      });
    }
  },

  // 更新系统状态
  updateSystemStatus(data: any) {
    const status = data.status;
    const statusMap = {
      'healthy': {
        status: 'normal',
        text: '系统运行正常',
        icon: '/images/icon-system-normal.png'
      },
      'warning': {
        status: 'warning',
        text: '系统存在警告',
        icon: '/images/icon-system-warning.png'
      },
      'error': {
        status: 'error',
        text: '系统运行异常',
        icon: '/images/icon-system-error.png'
      }
    };
    
    const statusInfo = statusMap[status] || statusMap['error'];
    
    this.setData({
      systemStatus: statusInfo.status,
      systemStatusText: statusInfo.text,
      systemStatusIcon: statusInfo.icon
    });
  },

  // 更新ERP状态
  updateErpStatus(data: any) {
    const status = data.status || 'unknown';
    const responseTime = data.avg_response_time || 0;
    const successRate = data.success_rate || 0;
    const todayRequests = data.today_requests || 0;
    
    this.setData({
      erpStatus: status,
      erpResponseTime: Math.round(responseTime),
      erpSuccessRate: Math.round(successRate * 100),
      erpTodayRequests: todayRequests
    });
  },

  // 更新微信API状态
  updateWechatStatus(data: any) {
    const status = data.status || 'unknown';
    const responseTime = data.avg_response_time || 0;
    const successRate = data.success_rate || 0;
    const todayCalls = data.today_calls || 0;
    
    this.setData({
      wechatStatus: status,
      wechatResponseTime: Math.round(responseTime),
      wechatSuccessRate: Math.round(successRate * 100),
      wechatTodayCalls: todayCalls
    });
  },

  // 更新性能指标
  updatePerformanceMetrics(data: any) {
    const avgResponseTime = data.avg_response_time || 0;
    const avgSuccessRate = data.avg_success_rate || 0;
    const totalRequests = data.total_requests || 0;
    
    // 计算趋势
    const responseTimeTrend = this.calculateTrend(data.response_time_trend);
    const successRateTrend = this.calculateTrend(data.success_rate_trend);
    const requestsTrend = this.calculateTrend(data.requests_trend);
    
    this.setData({
      avgResponseTime: Math.round(avgResponseTime),
      avgSuccessRate: Math.round(avgSuccessRate * 100),
      totalRequests: totalRequests,
      avgResponseTimeTrend: responseTimeTrend.direction,
      avgResponseTimeTrendText: responseTimeTrend.text,
      avgSuccessRateTrend: successRateTrend.direction,
      avgSuccessRateTrendText: successRateTrend.text,
      totalRequestsTrend: requestsTrend.direction,
      totalRequestsTrendText: requestsTrend.text,
      performanceData: {
        responseTimeData: data.response_time_history || [],
        requestCountData: data.request_count_history || [],
        labels: data.time_labels || []
      }
    });
    
    // 更新错误日志
    if (data.recent_errors) {
      this.setData({
        errorLogs: data.recent_errors.map((log: any) => ({
          logId: log.id,
          time: formatDate(new Date(log.timestamp), 'MM-DD HH:mm:ss'),
          level: log.level,
          levelText: this.getLevelText(log.level),
          message: log.message,
          source: log.source
        }))
      });
    }
  },

  // 计算趋势
  calculateTrend(trendData: any) {
    if (!trendData || trendData.length < 2) {
      return { direction: 'stable', text: '稳定' };
    }
    
    const recent = trendData[trendData.length - 1];
    const previous = trendData[trendData.length - 2];
    
    if (recent > previous) {
      return { direction: 'up', text: '上升' };
    } else if (recent < previous) {
      return { direction: 'down', text: '下降' };
    } else {
      return { direction: 'stable', text: '稳定' };
    }
  },

  // 获取级别文本
  getLevelText(level: string): string {
    const levelMap: { [key: string]: string } = {
      'error': '错误',
      'warning': '警告',
      'info': '信息',
      'debug': '调试'
    };
    return levelMap[level] || level;
  },

  // 绘制图表
  drawCharts() {
    this.drawResponseTimeChart();
    this.drawRequestCountChart();
  },

  // 绘制响应时间图表
  drawResponseTimeChart() {
    const ctx = wx.createCanvasContext('responseTimeChart', this);
    const data = this.data.performanceData.responseTimeData;
    const labels = this.data.performanceData.labels;
    
    if (!data || data.length === 0) return;
    
    const maxValue = Math.max(...data);
    const minValue = Math.min(...data);
    const range = maxValue - minValue || 1;
    
    // 设置画布尺寸
    const canvasWidth = 300;
    const canvasHeight = 150;
    const padding = 20;
    const chartWidth = canvasWidth - 2 * padding;
    const chartHeight = canvasHeight - 2 * padding;
    
    // 清除画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // 绘制网格线
    ctx.setStrokeStyle('#f0f0f0');
    ctx.setLineWidth(1);
    for (let i = 0; i <= 4; i++) {
      const y = padding + (chartHeight / 4) * i;
      ctx.moveTo(padding, y);
      ctx.lineTo(canvasWidth - padding, y);
    }
    ctx.stroke();
    
    // 绘制数据线
    ctx.setStrokeStyle('#667eea');
    ctx.setLineWidth(2);
    ctx.beginPath();
    
    data.forEach((value, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = canvasHeight - padding - ((value - minValue) / range) * chartHeight;
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    
    ctx.stroke();
    
    // 绘制数据点
    ctx.setFillStyle('#667eea');
    data.forEach((value, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = canvasHeight - padding - ((value - minValue) / range) * chartHeight;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
    
    ctx.draw();
  },

  // 绘制请求量图表
  drawRequestCountChart() {
    const ctx = wx.createCanvasContext('requestCountChart', this);
    const data = this.data.performanceData.requestCountData;
    const labels = this.data.performanceData.labels;
    
    if (!data || data.length === 0) return;
    
    const maxValue = Math.max(...data);
    const barWidth = 20;
    const barSpacing = 10;
    const canvasWidth = 300;
    const canvasHeight = 150;
    const padding = 20;
    
    // 清除画布
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // 绘制柱状图
    data.forEach((value, index) => {
      const x = padding + index * (barWidth + barSpacing);
      const height = (value / maxValue) * (canvasHeight - 2 * padding);
      const y = canvasHeight - padding - height;
      
      // 绘制柱子
      const gradient = ctx.createLinearGradient(x, y, x, canvasHeight - padding);
      gradient.addColorStop(0, '#667eea');
      gradient.addColorStop(1, '#764ba2');
      
      ctx.setFillStyle(gradient);
      ctx.fillRect(x, y, barWidth, height);
      
      // 绘制数值
      ctx.setFillStyle('#333333');
      ctx.setFontSize(10);
      ctx.setTextAlign('center');
      ctx.fillText(String(value), x + barWidth / 2, y - 5);
    });
    
    ctx.draw();
  }
});
