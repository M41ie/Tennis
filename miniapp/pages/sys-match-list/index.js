const BASE_URL = getApp().globalData.BASE_URL;
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
function displayFormat(fmt) {
  return FORMAT_DISPLAY[fmt] || fmt;
}
Page({
  data: { records: [] },
  onLoad() {
    this.fetchRecords();
  },
  fetchRecords() {
    const that = this;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    wx.request({
      url: `${BASE_URL}/sys/matches`,
      success(res) {
        const list = res.data || [];
        list.forEach(rec => {
          rec.scoreA = rec.score_a;
          rec.scoreB = rec.score_b;
          rec.playerAName = rec.a_name || rec.player_a;
          rec.playerBName = rec.b_name || rec.player_b;
          rec.playerAAvatar = rec.a_avatar || placeholder;
          rec.playerBAvatar = rec.b_avatar || placeholder;
          rec.ratingA = rec.a_after != null ? Number(rec.a_after).toFixed(3) : '';
          rec.ratingB = rec.b_after != null ? Number(rec.b_after).toFixed(3) : '';
          if (rec.a_after != null && rec.a_before != null) {
            const d = rec.a_after - rec.a_before;
            const abs = Math.abs(d).toFixed(3);
            rec.deltaDisplayA = (d > 0 ? '+' : d < 0 ? '-' : '') + abs;
            rec.deltaClassA = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
          } else {
            rec.deltaDisplayA = '';
            rec.deltaClassA = 'neutral';
          }
          if (rec.b_after != null && rec.b_before != null) {
            const d = rec.b_after - rec.b_before;
            const abs = Math.abs(d).toFixed(3);
            rec.deltaDisplayB = (d > 0 ? '+' : d < 0 ? '-' : '') + abs;
            rec.deltaClassB = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
          } else {
            rec.deltaDisplayB = '';
            rec.deltaClassB = 'neutral';
          }
          rec.displayFormat = displayFormat(rec.format);
        });
        that.setData({ records: list });
      }
    });
  }
});
