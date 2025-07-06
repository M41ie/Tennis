const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const optimisticUpdate = require('../../utils/optimistic');
const { withBase } = require('../../utils/format');
const ensureSubscribe = require('../../utils/ensureSubscribe');

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
    isAdmin: false,
    isLoading: true,
    isError: false,
    isEmpty: false
  },
  hideKeyboard,
  onLoad(options) {
    const tabIndex = options && options.tab ? Number(options.tab) : 0;
    const pendingTab = options && options.pending ? Number(options.pending) : 0;
    const modeIdx = options && options.mode ? Number(options.mode) : 0;
    this.setData({
      userId: store.userId,
      tabIndex,
      pendingTabIndex: pendingTab,
      modeIndex: modeIdx,
      doubles: modeIdx == 1,
      page: 1,
      finished: false,
      records: [],
    });
    if (tabIndex == 0) {
      this.fetchRecords();
    } else {
      this.fetchPendings();
    }
  },
  switchTab(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ tabIndex: idx });
    if (idx == 0) {
      this.setData({ page: 1, records: [], finished: false, isLoading: true, isError: false, isEmpty: false });
      this.fetchRecords();
    } else {
      this.fetchPendings();
    }
  },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx, doubles: idx == 1, page: 1, records: [], finished: false, isLoading: true, isError: false, isEmpty: false });
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
    this.setData({ isLoading: this.data.page === 1, isError: false, isEmpty: false });
    request({
      url: `${BASE_URL}/players/${userId}`,
      loading: false,
      success(res) {
        const player = res.data || {};
        const path = that.data.doubles ? 'doubles_records' : 'records';
        request({
          url: `${BASE_URL}/players/${userId}/${path}?limit=${limit}&offset=${offset}`,
          loading: false,
          success(r) {
            const list = r.data || [];
            list.forEach(rec => {
              rec.scoreA = rec.self_score;
              rec.scoreB = rec.opponent_score;
              rec.playerAName = player.name || '';
              rec.playerAAvatar = withBase(player.avatar_url || player.avatar) || placeholder;
              rec.ratingA = rec.self_rating_after != null ? Number(rec.self_rating_after).toFixed(3) : '';
              const d = rec.self_delta;
              if (d != null) {
                const delta = Number(d);
                const abs = Math.abs(delta).toFixed(3);
                rec.deltaDisplayA = (delta > 0 ? '+' : delta < 0 ? '-' : '') + abs;
                rec.deltaClassA = delta > 0 ? 'pos' : delta < 0 ? 'neg' : 'neutral';
              } else {
                rec.deltaDisplayA = '';
                rec.deltaClassA = 'neutral';
              }

              if (!that.data.doubles) {
                rec.playerBName = rec.opponent || '';
                rec.playerBAvatar = withBase(rec.opponent_avatar) || placeholder;
                rec.ratingB = rec.opponent_rating_after != null ? Number(rec.opponent_rating_after).toFixed(3) : '';
                const d2 = rec.opponent_delta;
                if (d2 != null) {
                  const delta2 = Number(d2);
                  const abs2 = Math.abs(delta2).toFixed(3);
                  rec.deltaDisplayB = (delta2 > 0 ? '+' : delta2 < 0 ? '-' : '') + abs2;
                  rec.deltaClassB = delta2 > 0 ? 'pos' : delta2 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.deltaDisplayB = '';
                  rec.deltaClassB = 'neutral';
                }
              } else {
                rec.partnerName = rec.partner || '';
                rec.partnerAvatar = withBase(rec.partner_avatar) || placeholder;
                rec.partnerRating = rec.partner_rating_after != null ? Number(rec.partner_rating_after).toFixed(3) : '';
                const pd = rec.partner_delta;
                if (pd != null) {
                  const deltaP = Number(pd);
                  const abs = Math.abs(deltaP).toFixed(3);
                  rec.partnerDeltaDisplay = (deltaP > 0 ? '+' : deltaP < 0 ? '-' : '') + abs;
                  rec.partnerDeltaClass = deltaP > 0 ? 'pos' : deltaP < 0 ? 'neg' : 'neutral';
                } else {
                  rec.partnerDeltaDisplay = '';
                  rec.partnerDeltaClass = 'neutral';
                }

                rec.opp1Name = rec.opponent1 || '';
                rec.opp1Avatar = withBase(rec.opponent1_avatar) || placeholder;
                rec.opp1Rating = rec.opponent1_rating_after != null ? Number(rec.opponent1_rating_after).toFixed(3) : '';
                const od1 = rec.opponent1_delta;
                if (od1 != null) {
                  const delta1 = Number(od1);
                  const abs = Math.abs(delta1).toFixed(3);
                  rec.opp1DeltaDisplay = (delta1 > 0 ? '+' : delta1 < 0 ? '-' : '') + abs;
                  rec.opp1DeltaClass = delta1 > 0 ? 'pos' : delta1 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.opp1DeltaDisplay = '';
                  rec.opp1DeltaClass = 'neutral';
                }

                rec.opp2Name = rec.opponent2 || '';
                rec.opp2Avatar = withBase(rec.opponent2_avatar) || placeholder;
                rec.opp2Rating = rec.opponent2_rating_after != null ? Number(rec.opponent2_rating_after).toFixed(3) : '';
                const od2 = rec.opponent2_delta;
                if (od2 != null) {
                  const delta2 = Number(od2);
                  const abs = Math.abs(delta2).toFixed(3);
                  rec.opp2DeltaDisplay = (delta2 > 0 ? '+' : delta2 < 0 ? '-' : '') + abs;
                  rec.opp2DeltaClass = delta2 > 0 ? 'pos' : delta2 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.opp2DeltaDisplay = '';
                  rec.opp2DeltaClass = 'neutral';
                }
              }

              rec.displayFormat = displayFormat(rec.format);
            });
            if (that.data.page === 1) {
              that.setData({
                records: list,
                finished: list.length < limit,
                isLoading: false,
                isEmpty: list.length === 0
              });
            } else {
              const start = that.data.records.length;
              const obj = { finished: list.length < limit, isLoading: false };
              list.forEach((item, i) => {
                obj[`records[${start + i}]`] = item;
              });
              that.setData(obj);
            }
          }
        });
      },
      fail() {
        that.setData({ isLoading: false, isError: true });
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
      loading: false,
      data: { token },
      success(r) {
        if (r.statusCode >= 300) {
          wx.showToast({ duration: 4000,  title: '加载失败', icon: 'none' });
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
          it.playerAAvatar = withBase(it.player_a_avatar) || placeholder;
          it.playerBAvatar = withBase(it.player_b_avatar) || placeholder;
          it.ratingA = it.rating_a_before != null ? Number(it.rating_a_before).toFixed(3) : '';
          it.ratingB = it.rating_b_before != null ? Number(it.rating_b_before).toFixed(3) : '';
          it.displayFormat = it.format_name ? displayFormat(it.format_name) : '';
          it.location = it.location || '';
          return it;
        });
        that.setData({ pendingSingles: list });
      },
      fail() {
        wx.showToast({ duration: 4000,  title: '网络错误', icon: 'none' });
      }
    });

    request({
      url: `${BASE_URL}/players/${userId}/pending_doubles`,
      loading: false,
      data: { token },
      success(r) {
        if (r.statusCode >= 300) {
          wx.showToast({ duration: 4000,  title: '加载失败', icon: 'none' });
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
        that.setData({ pendingDoubles: list });
      },
      fail() {
        wx.showToast({ duration: 4000,  title: '网络错误', icon: 'none' });
      }
    });
  },
  confirmSingle(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    ensureSubscribe('match').then(() => {
      optimisticUpdate(this, 'pendingSingles', idx, () =>
        request({
          url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/confirm`,
          method: 'POST',
          data: { user_id: this.data.userId, token }
        })
      ).finally(() => {
        this.fetchPendings();
      });
    });
  },
  approveSingle(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/approve`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ duration: 4000,  title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ duration: 4000,  title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  vetoSingle(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    optimisticUpdate(this, 'pendingSingles', idx, () =>
      request({
        url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/veto`,
        method: 'POST',
        data: { approver: this.data.userId, token }
      })
    ).finally(() => {
      this.fetchPendings();
    });
  },
  rejectSingle(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    optimisticUpdate(this, 'pendingSingles', idx, () =>
      request({
        url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/reject`,
        method: 'POST',
        data: { user_id: this.data.userId, token }
      })
    ).finally(() => {
      this.fetchPendings();
    });
  },
  confirmDouble(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    ensureSubscribe('match').then(() => {
      optimisticUpdate(this, 'pendingDoubles', idx, () =>
        request({
          url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/confirm`,
          method: 'POST',
          data: { user_id: this.data.userId, token }
        })
      ).finally(() => {
        this.fetchPendings();
      });
    });
  },
  approveDouble(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/approve`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ duration: 4000,  title: '错误', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ duration: 4000,  title: '网络错误', icon: 'none' });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  vetoDouble(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    optimisticUpdate(this, 'pendingDoubles', idx, () =>
      request({
        url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/veto`,
        method: 'POST',
        data: { approver: this.data.userId, token }
      })
    ).finally(() => {
      this.fetchPendings();
    });
  },
  rejectDouble(e) {
    const idx = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.club;
    const token = store.token;
    optimisticUpdate(this, 'pendingDoubles', idx, () =>
      request({
        url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/reject`,
        method: 'POST',
        data: { user_id: this.data.userId, token }
      })
    ).finally(() => {
      this.fetchPendings();
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
  // Allow users to manually subscribe to match notifications via a
  // button tap, which properly triggers the subscription prompt.
  subscribeMatch() {
    ensureSubscribe('match');
  },
  addMatch() {
    // Request subscription to match notifications when the user
    // actively creates a new match. This satisfies WeChat's requirement
    // that subscription prompts be triggered by a user interaction.
    ensureSubscribe('match').finally(() => {
      wx.navigateTo({ url: '/pages/addmatch/addmatch' });
    });
  },
  onPullDownRefresh() {
    this.setData({ page: 1, records: [], finished: false, isLoading: true, isError: false, isEmpty: false });
    this.fetchRecords();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished || this.data.tabIndex !== 0) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchRecords();
  }
});
