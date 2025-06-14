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
  data: { records: [], doubles: false, modeIndex: 0, page: 1, finished: false },
  onLoad() {
    this.fetchRecords();
  },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx, doubles: idx == 1, page: 1, records: [], finished: false });
    this.fetchRecords();
  },
  fetchRecords() {
    const that = this;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    const limit = 10;
    const offset = (this.data.page - 1) * limit;
    const url = this.data.doubles ? `${BASE_URL}/sys/doubles` : `${BASE_URL}/sys/matches`;
    wx.request({
      url: `${url}?limit=${limit}&offset=${offset}`,
      success(res) {
        const list = res.data || [];
        list.forEach(rec => {
          rec.scoreA = rec.score_a;
          rec.scoreB = rec.score_b;
          if (!that.data.doubles) {
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
          } else {
            rec.playerAName = rec.a1_name || rec.a1;
            rec.partnerName = rec.a2_name || rec.a2;
            rec.opp1Name = rec.b1_name || rec.b1;
            rec.opp2Name = rec.b2_name || rec.b2;
            rec.playerAAvatar = rec.a1_avatar || placeholder;
            rec.partnerAvatar = rec.a2_avatar || placeholder;
            rec.opp1Avatar = rec.b1_avatar || placeholder;
            rec.opp2Avatar = rec.b2_avatar || placeholder;
            rec.ratingA = rec.rating_a1_after != null ? Number(rec.rating_a1_after).toFixed(3) : '';
            rec.partnerRating = rec.rating_a2_after != null ? Number(rec.rating_a2_after).toFixed(3) : '';
            rec.opp1Rating = rec.rating_b1_after != null ? Number(rec.rating_b1_after).toFixed(3) : '';
            rec.opp2Rating = rec.rating_b2_after != null ? Number(rec.rating_b2_after).toFixed(3) : '';
            // deltas
            const pd = rec.rating_a1_after != null && rec.rating_a1_before != null ? rec.rating_a1_after - rec.rating_a1_before : null;
            if (pd != null) {
              const abs = Math.abs(pd).toFixed(3);
              rec.deltaDisplayA = (pd > 0 ? '+' : pd < 0 ? '-' : '') + abs;
              rec.deltaClassA = pd > 0 ? 'pos' : pd < 0 ? 'neg' : 'neutral';
            }
          }
          rec.displayFormat = displayFormat(rec.format);
        });
        const records = that.data.page === 1 ? list : that.data.records.concat(list);
        that.setData({ records, finished: list.length < limit });
      }
    });
  },
  onPullDownRefresh() {
    this.setData({ page: 1, records: [], finished: false });
    this.fetchRecords();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchRecords();
  }
});
