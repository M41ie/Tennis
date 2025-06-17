const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const store = require('../../store/store');

// Map backend format identifiers to display names
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
  data: {
    tabIndex: 0,
    records: [],
    doubles: false,
    modeIndex: 0,
    page: 1,
    finished: false,
    pendingTabIndex: 0,
    pendingSingles: [],
    pendingDoubles: [],
    userId: '',
    isAdmin: false
  },
  onLoad() {
    this.setData({ userId: store.userId, page: 1, finished: false, records: [] });
    this.fetchRecords();
    this.fetchPendings();
  },
  switchTab(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ tabIndex: idx });
    if (idx == 0) {
      this.setData({ page: 1, records: [], finished: false });
      this.fetchRecords();
    } else {
      this.fetchPendings();
    }
  },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx, doubles: idx == 1, page: 1, records: [], finished: false });
    this.fetchRecords();
  },
  switchPendingMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ pendingTabIndex: idx });
  },
  fetchRecords() {
    const userId = store.userId;
    if (!userId) return;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    const that = this;
    const limit = 10;
    const offset = (this.data.page - 1) * limit;
    request({
      url: `${BASE_URL}/players/${userId}`,
      success(res) {
        const player = res.data || {};
        const path = that.data.doubles ? 'doubles_records' : 'records';
        request({
          url: `${BASE_URL}/players/${userId}/${path}?limit=${limit}&offset=${offset}`,
          success(r) {
            const list = r.data || [];
            list.forEach(rec => {
              rec.scoreA = rec.self_score;
              rec.scoreB = rec.opponent_score;
              rec.playerAName = player.name || '';
              rec.playerAAvatar = player.avatar_url || player.avatar || placeholder;
              rec.ratingA = rec.self_rating_after != null ? rec.self_rating_after.toFixed(3) : '';
              const d = rec.self_delta;
              if (d != null) {
                const abs = Math.abs(d).toFixed(3);
                rec.deltaDisplayA = (d > 0 ? '+' : d < 0 ? '-' : '') + abs;
                rec.deltaClassA = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
              } else {
                rec.deltaDisplayA = '';
                rec.deltaClassA = 'neutral';
              }

              if (!that.data.doubles) {
                rec.playerBName = rec.opponent || '';
                rec.playerBAvatar = rec.opponent_avatar || placeholder;
                rec.ratingB = rec.opponent_rating_after != null ? rec.opponent_rating_after.toFixed(3) : '';
                const d2 = rec.opponent_delta;
                if (d2 != null) {
                  const abs2 = Math.abs(d2).toFixed(3);
                  rec.deltaDisplayB = (d2 > 0 ? '+' : d2 < 0 ? '-' : '') + abs2;
                  rec.deltaClassB = d2 > 0 ? 'pos' : d2 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.deltaDisplayB = '';
                  rec.deltaClassB = 'neutral';
                }
              } else {
                rec.partnerName = rec.partner || '';
                rec.partnerAvatar = rec.partner_avatar || placeholder;
                rec.partnerRating = rec.partner_rating_after != null ? rec.partner_rating_after.toFixed(3) : '';
                const pd = rec.partner_delta;
                if (pd != null) {
                  const abs = Math.abs(pd).toFixed(3);
                  rec.partnerDeltaDisplay = (pd > 0 ? '+' : pd < 0 ? '-' : '') + abs;
                  rec.partnerDeltaClass = pd > 0 ? 'pos' : pd < 0 ? 'neg' : 'neutral';
                } else {
                  rec.partnerDeltaDisplay = '';
                  rec.partnerDeltaClass = 'neutral';
                }

                rec.opp1Name = rec.opponent1 || '';
                rec.opp1Avatar = rec.opponent1_avatar || placeholder;
                rec.opp1Rating = rec.opponent1_rating_after != null ? rec.opponent1_rating_after.toFixed(3) : '';
                const od1 = rec.opponent1_delta;
                if (od1 != null) {
                  const abs = Math.abs(od1).toFixed(3);
                  rec.opp1DeltaDisplay = (od1 > 0 ? '+' : od1 < 0 ? '-' : '') + abs;
                  rec.opp1DeltaClass = od1 > 0 ? 'pos' : od1 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.opp1DeltaDisplay = '';
                  rec.opp1DeltaClass = 'neutral';
                }

                rec.opp2Name = rec.opponent2 || '';
                rec.opp2Avatar = rec.opponent2_avatar || placeholder;
                rec.opp2Rating = rec.opponent2_rating_after != null ? rec.opponent2_rating_after.toFixed(3) : '';
                const od2 = rec.opponent2_delta;
                if (od2 != null) {
                  const abs = Math.abs(od2).toFixed(3);
                  rec.opp2DeltaDisplay = (od2 > 0 ? '+' : od2 < 0 ? '-' : '') + abs;
                  rec.opp2DeltaClass = od2 > 0 ? 'pos' : od2 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.opp2DeltaDisplay = '';
                  rec.opp2DeltaClass = 'neutral';
                }
              }

              rec.displayFormat = displayFormat(rec.format);
            });
            const records =
              that.data.page === 1 ? list : that.data.records.concat(list);
            that.setData({
              records,
              finished: list.length < limit,
            });
          }
        });
      }
    });
  },
  fetchClubInfo() {
    this.fetchPendings();
  },
  fetchPendings() {
    const userId = store.userId;
    const token = store.token;
    if (!userId || !token) return;
    const that = this;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;

    request({
      url: `${BASE_URL}/players/${userId}/pending_matches`,
      data: { token },
      success(r) {
        if (r.statusCode >= 300) {
          wx.showToast({ title: '加载失败', icon: 'none' });
          return;
        }
        const list = r.data.map(it => {
          const confirmedA = Boolean(it.confirmed_a);
          const confirmedB = Boolean(it.confirmed_b);
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.statusText = it.display_status_text || '';
          it.canApprove = it.can_approve;
          it.canVeto = it.can_veto;
          it.canShare = it.status !== 'vetoed' && it.status !== 'rejected';
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
        that.setData({ pendingSingles: list });
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });

    request({
      url: `${BASE_URL}/players/${userId}/pending_doubles`,
      data: { token },
      success(r) {
        if (r.statusCode >= 300) {
          wx.showToast({ title: '加载失败', icon: 'none' });
          return;
        }
        const list = r.data.map(it => {
          const confirmedA = Boolean(it.confirmed_a);
          const confirmedB = Boolean(it.confirmed_b);
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
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
        that.setData({ pendingDoubles: list });
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
  },
  confirmSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/confirm`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  approveSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/approve`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  vetoSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    // Optimistically remove the item for immediate feedback
    const arr = this.data.pendingSingles.slice();
    const pos = arr.findIndex(it => it.index === idx);
    if (pos !== -1) {
      arr.splice(pos, 1);
      this.setData({ pendingSingles: arr });
    }
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/veto`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      complete() {
        that.fetchPendings();
      }
    });
  },
  rejectSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/reject`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  confirmDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/confirm`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  approveDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/approve`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  vetoDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    // Optimistically remove the item for immediate feedback
    const arr = this.data.pendingDoubles.slice();
    const pos = arr.findIndex(it => it.index === idx);
    if (pos !== -1) {
      arr.splice(pos, 1);
      this.setData({ pendingDoubles: arr });
    }
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/veto`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      complete() {
        that.fetchPendings();
      }
    });
  },
  rejectDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/reject`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  viewRecord(e) {
    const rec = this.data.records[e.currentTarget.dataset.index];
    wx.navigateTo({
      url:
        '/pages/recorddetail/recorddetail?data=' +
        encodeURIComponent(JSON.stringify(rec))
    });
  },
  addMatch() {
    wx.navigateTo({ url: '/pages/addmatch/addmatch' });
  },
  onPullDownRefresh() {
    this.setData({ page: 1, records: [], finished: false });
    this.fetchRecords();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished || this.data.tabIndex !== 0) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchRecords();
  }
});
