const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const store = require('../../store/store');
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
  data: { modeIndex: 0, singles: [], doublesList: [], approving: false },
  hideKeyboard,
  onLoad() { this.fetchPendings(); },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx });
    this.fetchPendings();
  },
  fetchPendings() {
    const token = store.token;
    if (!token) return;
    const that = this;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    if (this.data.modeIndex === 0) {
      request({
        url: `${BASE_URL}/sys/pending_matches`,
        data: { token },
        success(res) {
          const list = (res.data || []).map(it => {
            it.statusText = it.display_status_text || '';
            it.canApprove = it.can_approve;
            it.canVeto = it.can_veto;
            it.canShare = it.status !== 'vetoed' && it.status !== 'rejected';
            it.scoreA = it.score_a;
            it.scoreB = it.score_b;
            it.playerAName = it.player_a_name || it.player_a;
            it.playerBName = it.player_b_name || it.player_b;
            it.playerAAvatar = withBase(it.player_a_avatar) || placeholder;
            it.playerBAvatar = withBase(it.player_b_avatar) || placeholder;
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
      request({
        url: `${BASE_URL}/sys/pending_doubles`,
        data: { token },
        success(res) {
          const list = (res.data || []).map(it => {
            it.statusText = it.display_status_text || '';
            it.canApprove = it.can_approve;
            it.canVeto = it.can_veto;
            it.canShare = it.status !== 'vetoed' && it.status !== 'rejected';
            it.scoreA = it.score_a;
            it.scoreB = it.score_b;
            it.playerAName = it.a1_name || it.a1;
            it.partnerName = it.a2_name || it.a2;
            it.opp1Name = it.b1_name || it.b1;
            it.opp2Name = it.b2_name || it.b2;
            it.playerAAvatar = withBase(it.a1_avatar) || placeholder;
            it.partnerAvatar = withBase(it.a2_avatar) || placeholder;
            it.opp1Avatar = withBase(it.b1_avatar) || placeholder;
            it.opp2Avatar = withBase(it.b2_avatar) || placeholder;
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
    if (this.data.approving) return;
    const idx = e.currentTarget.dataset.id || e.detail.id;
    const cid = e.currentTarget.dataset.club;
    const that = this;
    this.setData({ approving: true });
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/approve`,
      method: 'POST',
      data: { approver: store.userId },
      fail() { wx.showToast({ duration: 4000, title: '操作失败', icon: 'none' }); },
      complete() {
        that.setData({ approving: false });
        that.fetchPendings();
      }
    });
  },
  vetoSingle(e) {
    if (this.data.approving) return;
    const idx = e.currentTarget.dataset.id || e.detail.id;
    const cid = e.currentTarget.dataset.club;
    const that = this;
    // Optimistically remove the item so the UI updates immediately
    const arr = this.data.singles.slice();
    const pos = arr.findIndex(it => it.id === idx);
    if (pos !== -1) {
      arr.splice(pos, 1);
      this.setData({ singles: arr });
    }
    this.setData({ approving: true });
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/veto`,
      method: 'POST',
      data: { approver: store.userId },
      complete() {
        that.setData({ approving: false });
        that.fetchPendings();
      }
    });
  },
  approveDouble(e) {
    if (this.data.approving) return;
    const idx = e.currentTarget.dataset.id || e.detail.id;
    const cid = e.currentTarget.dataset.club;
    const that = this;
    this.setData({ approving: true });
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/approve`,
      method: 'POST',
      data: { approver: store.userId },
      fail() { wx.showToast({ duration: 4000, title: '操作失败', icon: 'none' }); },
      complete() {
        that.setData({ approving: false });
        that.fetchPendings();
      }
    });
  },
  vetoDouble(e) {
    if (this.data.approving) return;
    const idx = e.currentTarget.dataset.id || e.detail.id;
    const cid = e.currentTarget.dataset.club;
    const that = this;
    // Optimistically remove the item so the UI updates immediately
    const arr = this.data.doublesList.slice();
    const pos = arr.findIndex(it => it.id === idx);
    if (pos !== -1) {
      arr.splice(pos, 1);
      this.setData({ doublesList: arr });
    }
    this.setData({ approving: true });
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/veto`,
      method: 'POST',
      data: { approver: store.userId },
      complete() {
        that.setData({ approving: false });
        that.fetchPendings();
      }
    });
  }
});
