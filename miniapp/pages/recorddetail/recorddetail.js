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
        if (rec.self_delta != null) {
          const d = rec.self_delta;
          rec.deltaClass = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
          const sign = d > 0 ? '+' : d < 0 ? '' : '';
          rec.deltaDisplay = sign + d.toFixed(3);
        }
        this.setData({ record: rec });
      } catch (e) {}
    }
  },
  noAccess() {
    wx.showToast({ title: '暂无权限', icon: 'none' });
  }
});
