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
  data: { modeIndex: 0, singles: [], doublesList: [] },
  onLoad() { this.fetchPendings(); },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx });
    this.fetchPendings();
  },
  fetchPendings() {
    const token = wx.getStorageSync('token');
    if (!token) return;
    const that = this;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    if (this.data.modeIndex === 0) {
      wx.request({
        url: `${BASE_URL}/sys/pending_matches`,
        data: { token },
        success(res) {
          const list = (res.data || []).map(it => {
            it.statusText = it.display_status_text || '';
            it.canApprove = it.can_approve;
            it.canVeto = it.can_veto;
            it.scoreA = it.score_a;
            it.scoreB = it.score_b;
            it.playerAName = it.player_a_name || it.player_a;
            it.playerBName = it.player_b_name || it.player_b;
            it.playerAAvatar = it.player_a_avatar || placeholder;
            it.playerBAvatar = it.player_b_avatar || placeholder;
            it.ratingA = it.rating_a_before != null ? Number(it.rating_a_before).toFixed(3) : '';
            it.ratingB = it.rating_b_before != null ? Number(it.rating_b_before).toFixed(3) : '';
            it.displayFormat = it.format_name ? displayFormat(it.format_name) : '';
            it.location = it.location || '';
            return it;
          });
          that.setData({ singles: list });
        }
      });
    } else {
      wx.request({
        url: `${BASE_URL}/sys/pending_doubles`,
        data: { token },
        success(res) {
          const list = (res.data || []).map(it => {
            it.statusText = it.display_status_text || '';
            it.canApprove = it.can_approve;
            it.canVeto = it.can_veto;
            it.scoreA = it.score_a;
            it.scoreB = it.score_b;
            it.playerAName = it.a1_name || it.a1;
            it.partnerName = it.a2_name || it.a2;
            it.opp1Name = it.b1_name || it.b1;
            it.opp2Name = it.b2_name || it.b2;
            it.playerAAvatar = it.a1_avatar || placeholder;
            it.partnerAvatar = it.a2_avatar || placeholder;
            it.opp1Avatar = it.b1_avatar || placeholder;
            it.opp2Avatar = it.b2_avatar || placeholder;
            it.ratingA = it.rating_a1_before != null ? Number(it.rating_a1_before).toFixed(3) : '';
            it.partnerRating = it.rating_a2_before != null ? Number(it.rating_a2_before).toFixed(3) : '';
            it.opp1Rating = it.rating_b1_before != null ? Number(it.rating_b1_before).toFixed(3) : '';
            it.opp2Rating = it.rating_b2_before != null ? Number(it.rating_b2_before).toFixed(3) : '';
            it.displayFormat = it.format_name ? displayFormat(it.format_name) : '';
            it.location = it.location || '';
            return it;
          });
          that.setData({ doublesList: list });
        }
      });
    }
  },
  approveSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/approve`,
      method: 'POST',
      data: { approver: wx.getStorageSync('user_id'), token },
      complete() { that.fetchPendings(); }
    });
  },
  vetoSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/veto`,
      method: 'POST',
      data: { approver: wx.getStorageSync('user_id'), token },
      complete() { that.fetchPendings(); }
    });
  },
  approveDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/approve`,
      method: 'POST',
      data: { approver: wx.getStorageSync('user_id'), token },
      complete() { that.fetchPendings(); }
    });
  },
  vetoDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/veto`,
      method: 'POST',
      data: { approver: wx.getStorageSync('user_id'), token },
      complete() { that.fetchPendings(); }
    });
  }
});
