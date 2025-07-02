const FORMAT_DISPLAY = {
  '6_game': '六局',
  '4_game': '四局',
  tb10: '抢十',
  tb7: '抢七',
  '6局': '六局',
  '4局': '四局',
  '抢10': '抢十',
  '抢7': '抢七'
};
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { t } = require('../../utils/locales');

function displayFormat(fmt) {
  return FORMAT_DISPLAY[fmt] || fmt;
}

Page({
  data: {
    t,
    record: null
  },
  hideKeyboard,
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
          const delta = Number(d);
          const abs = Math.abs(delta).toFixed(3);
          rec.deltaDisplay = (delta > 0 ? '+' : delta < 0 ? '-' : '') + abs;
          rec.deltaClass = delta > 0 ? 'pos' : delta < 0 ? 'neg' : 'neutral';
        } else {
          rec.deltaDisplay = '';
          rec.deltaClass = 'neutral';
        }
        if (rec.self_rating_after != null)
          rec.self_rating_after = Number(rec.self_rating_after).toFixed(3);
        rec.displayFormat = displayFormat(rec.format);
        this.setData({ record: rec });
      } catch (e) {}
    }
  },
  noAccess() {
    wx.showToast({ duration: 4000,  title: t.noAccess, icon: 'none' });
  }
});
