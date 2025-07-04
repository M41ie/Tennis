const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { withBase } = require('../../utils/format');
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
  hideKeyboard,
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
    request({
      url: `${url}?limit=${limit}&offset=${offset}`,
      success(res) {
        const list = res.data || [];
        list.forEach(rec => {
          rec.scoreA = rec.score_a;
          rec.scoreB = rec.score_b;
          if (!that.data.doubles) {
            rec.playerAName = rec.a_name || rec.player_a;
            rec.playerBName = rec.b_name || rec.player_b;
            rec.playerAAvatar = withBase(rec.a_avatar) || placeholder;
            rec.playerBAvatar = withBase(rec.b_avatar) || placeholder;
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
            rec.playerAAvatar = withBase(rec.a1_avatar) || placeholder;
            rec.partnerAvatar = withBase(rec.a2_avatar) || placeholder;
            rec.opp1Avatar = withBase(rec.b1_avatar) || placeholder;
            rec.opp2Avatar = withBase(rec.b2_avatar) || placeholder;
            rec.ratingA = rec.rating_a1_after != null ? Number(rec.rating_a1_after).toFixed(3) : '';
            rec.partnerRating = rec.rating_a2_after != null ? Number(rec.rating_a2_after).toFixed(3) : '';
            rec.opp1Rating = rec.rating_b1_after != null ? Number(rec.rating_b1_after).toFixed(3) : '';
            rec.opp2Rating = rec.rating_b2_after != null ? Number(rec.rating_b2_after).toFixed(3) : '';
            // deltas for all participants
            const dA1 = rec.rating_a1_after != null && rec.rating_a1_before != null ? rec.rating_a1_after - rec.rating_a1_before : null;
            if (dA1 != null) {
              const abs = Math.abs(dA1).toFixed(3);
              rec.deltaDisplayA = (dA1 > 0 ? '+' : dA1 < 0 ? '-' : '') + abs;
              rec.deltaClassA = dA1 > 0 ? 'pos' : dA1 < 0 ? 'neg' : 'neutral';
            }
            const dA2 = rec.rating_a2_after != null && rec.rating_a2_before != null ? rec.rating_a2_after - rec.rating_a2_before : null;
            if (dA2 != null) {
              const abs = Math.abs(dA2).toFixed(3);
              rec.partnerDeltaDisplay = (dA2 > 0 ? '+' : dA2 < 0 ? '-' : '') + abs;
              rec.partnerDeltaClass = dA2 > 0 ? 'pos' : dA2 < 0 ? 'neg' : 'neutral';
            }
            const dB1 = rec.rating_b1_after != null && rec.rating_b1_before != null ? rec.rating_b1_after - rec.rating_b1_before : null;
            if (dB1 != null) {
              const abs = Math.abs(dB1).toFixed(3);
              rec.opp1DeltaDisplay = (dB1 > 0 ? '+' : dB1 < 0 ? '-' : '') + abs;
              rec.opp1DeltaClass = dB1 > 0 ? 'pos' : dB1 < 0 ? 'neg' : 'neutral';
            }
            const dB2 = rec.rating_b2_after != null && rec.rating_b2_before != null ? rec.rating_b2_after - rec.rating_b2_before : null;
            if (dB2 != null) {
              const abs = Math.abs(dB2).toFixed(3);
              rec.opp2DeltaDisplay = (dB2 > 0 ? '+' : dB2 < 0 ? '-' : '') + abs;
              rec.opp2DeltaClass = dB2 > 0 ? 'pos' : dB2 < 0 ? 'neg' : 'neutral';
            }
          }
          rec.displayFormat = displayFormat(rec.format);
        });
        if (that.data.page === 1) {
          that.setData({ records: list, finished: list.length < limit });
        } else {
          const start = that.data.records.length;
          const obj = { finished: list.length < limit };
          list.forEach((item, i) => {
            obj[`records[${start + i}]`] = item;
          });
          that.setData(obj);
        }
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
