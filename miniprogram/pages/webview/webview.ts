Page({
  data: {
    url: ''
  },
  onLoad(options: any) {
    const { url } = options || {}
    if (url) {
      this.setData({ url: decodeURIComponent(url) })
    }
  }
})

