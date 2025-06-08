const BASE_URL = getApp().globalData.BASE_URL;

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
    pendingTabIndex: 0,
    pendingSingles: [],
    pendingDoubles: [],
    userId: '',
    isAdmin: false
  },
  onLoad() {
    this.setData({ userId: wx.getStorageSync('user_id') });
    this.fetchRecords();
    this.fetchClubInfo();
  },
  switchTab(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ tabIndex: idx });
    if (idx == 0) {
      this.fetchRecords();
    } else {
      this.fetchPendings();
    }
  },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx, doubles: idx == 1 });
    this.fetchRecords();
  },
  switchPendingMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ pendingTabIndex: idx });
  },
  fetchRecords() {
    const userId = wx.getStorageSync('user_id');
    const clubId = wx.getStorageSync('club_id');
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    const that = this;
    if (!userId || !clubId) return;
    wx.request({
      url: `${BASE_URL}/clubs/${clubId}/players`,
      success(res) {
        const players = res.data || [];
        const idMap = {};
        const nameMap = {};
        let player = null;
        players.forEach(p => {
          idMap[p.user_id] = p;
          nameMap[p.name] = p;
          if (p.user_id === userId) player = p;
        });
        if (player) {
          const path = that.data.doubles ? 'doubles_records' : 'records';
          wx.request({
            url: `${BASE_URL}/clubs/${clubId}/players/${userId}/${path}`,
            success(r) {
              const list = r.data || [];
              list.forEach(rec => {
                rec.scoreA = rec.self_score;
                rec.scoreB = rec.opponent_score;
                // singles fields
                rec.playerAName = player.name;
                rec.playerAAvatar = player.avatar || placeholder;
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
                  const opp = nameMap[rec.playerBName] || (rec.opponent_id && idMap[rec.opponent_id]);
                  rec.playerBAvatar = (rec.opponent_avatar || (opp && opp.avatar)) || placeholder;
                  rec.ratingB = rec.opponent_rating_after != null ? rec.opponent_rating_after.toFixed(3) : opp && opp.rating != null ? opp.rating.toFixed(3) : '';
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
                  // doubles partner
                  const partner = (rec.partner_id && idMap[rec.partner_id]) || nameMap[rec.partner || ''];
                  rec.partnerName = partner ? partner.name : rec.partner || '';
                  rec.partnerAvatar = (rec.partner_avatar || (partner && partner.avatar)) || placeholder;
                  rec.partnerRating = rec.partner_rating_after != null ? rec.partner_rating_after.toFixed(3) : partner && partner.rating != null ? partner.rating.toFixed(3) : '';
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
                  const o1 = (rec.opponent1_id && idMap[rec.opponent1_id]) || nameMap[rec.opp1Name];
                  if (o1) rec.opp1Name = o1.name;
                  rec.opp1Avatar = (rec.opponent1_avatar || (o1 && o1.avatar)) || placeholder;
                  rec.opp1Rating = rec.opponent1_rating_after != null ? rec.opponent1_rating_after.toFixed(3) : o1 && o1.rating != null ? o1.rating.toFixed(3) : '';
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
                  const o2 = (rec.opponent2_id && idMap[rec.opponent2_id]) || nameMap[rec.opp2Name];
                  if (o2) rec.opp2Name = o2.name;
                  rec.opp2Avatar = (rec.opponent2_avatar || (o2 && o2.avatar)) || placeholder;
                  rec.opp2Rating = rec.opponent2_rating_after != null ? rec.opponent2_rating_after.toFixed(3) : o2 && o2.rating != null ? o2.rating.toFixed(3) : '';
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
              that.setData({ records: list });
            }
          });
        }
      }
    });
  },
  fetchClubInfo() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data;
        const admin =
          info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId));
        that.setData({ isAdmin: admin });
      },
      complete() {
        that.fetchPendings();
      }
    });
  },
  fetchPendings() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    const token = wx.getStorageSync('token');
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players`,
      success(res) {
        const players = res.data || [];
        const idMap = {};
        players.forEach(p => {
          idMap[p.user_id] = p;
        });

        wx.request({
          url: `${BASE_URL}/clubs/${cid}/pending_matches`,
          data: { token },
          success(r) {
            if (r.statusCode >= 300) {
              wx.showToast({ title: '加载失败', icon: 'none' });
              return;
            }
            const uid = that.data.userId;
            const isAdmin = that.data.isAdmin;
            const list = r.data.map(it => {
              it.canConfirm = it.can_confirm;
              it.canReject = it.can_decline;
              it.statusText = it.display_status_text || '';
              it.canApprove = isAdmin && it.confirmed_a && it.confirmed_b;
              it.canVeto = isAdmin;
              const pa = idMap[it.player_a] || {};
              const pb = idMap[it.player_b] || {};
              it.scoreA = it.score_a;
              it.scoreB = it.score_b;
              it.playerAName = it.player_a_name || pa.name || it.player_a;
              it.playerBName = it.player_b_name || pb.name || it.player_b;
              it.playerAAvatar = pa.avatar || placeholder;
              it.playerBAvatar = pb.avatar || placeholder;
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

        wx.request({
          url: `${BASE_URL}/clubs/${cid}/pending_doubles`,
          data: { token },
          success(r) {
            if (r.statusCode >= 300) {
              wx.showToast({ title: '加载失败', icon: 'none' });
              return;
            }
            const isAdmin = that.data.isAdmin;
            const list = r.data.map(it => {
              it.canConfirm = it.can_confirm;
              it.canReject = it.can_decline;
              it.statusText = it.display_status_text || '';
              it.canApprove = isAdmin && it.confirmed_a && it.confirmed_b;
              it.canVeto = isAdmin;
              const a1 = idMap[it.a1] || {};
              const a2 = idMap[it.a2] || {};
              const b1 = idMap[it.b1] || {};
              const b2 = idMap[it.b2] || {};
              it.scoreA = it.score_a;
              it.scoreB = it.score_b;
              it.playerAName = it.a1_name || a1.name || it.a1;
              it.partnerName = it.a2_name || a2.name || it.a2;
              it.opp1Name = it.b1_name || b1.name || it.b1;
              it.opp2Name = it.b2_name || b2.name || it.b2;
              it.playerAAvatar = a1.avatar || placeholder;
              it.partnerAvatar = a2.avatar || placeholder;
              it.opp1Avatar = b1.avatar || placeholder;
              it.opp2Avatar = b2.avatar || placeholder;
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
      }
    });
  },
  confirmSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
  }
});
