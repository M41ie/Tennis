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
        const d = rec.self_delta;
        if (d != null) {
          const abs = Math.abs(d).toFixed(3);
          rec.deltaDisplay = (d > 0 ? '+' : d < 0 ? '-' : '') + abs;
          rec.deltaClass = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
        } else {
          rec.deltaDisplay = '';
          rec.deltaClass = 'neutral';
        }
        this.setData({ record: rec });
      } catch (e) {}
    }
  },
  noAccess() {
    wx.showToast({ title: '暂无权限', icon: 'none' });
  }
});
