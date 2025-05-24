Page({
  data: {
    record: null
  },
  onLoad(options) {
    if (options.data) {
      try {
        const rec = JSON.parse(decodeURIComponent(options.data));
        if (rec.expected_score != null) {
          rec.expected_score = (rec.expected_score * 100).toFixed(1) + '%';
        }
        if (rec.actual_rate != null) {
          rec.actual_rate = (rec.actual_rate * 100).toFixed(1) + '%';
        }
        this.setData({ record: rec });
      } catch (e) {}
    }
  },
  noAccess() {
    wx.showToast({ title: '暂无权限', icon: 'none' });
  }
});
