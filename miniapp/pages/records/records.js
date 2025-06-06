const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    tabIndex: 0,
    records: [],
    doubles: false,
    modeIndex: 0,
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
  fetchRecords() {
    const userId = wx.getStorageSync('user_id');
    const clubId = wx.getStorageSync('club_id');
    const that = this;
    if (!userId || !clubId) return;
    wx.request({
      url: `${BASE_URL}/clubs/${clubId}/players`,
      success(res) {
        const player = res.data.find(p => p.user_id === userId);
        if (player) {
          const path = that.data.doubles ? 'doubles_records' : 'records';
          wx.request({
            url: `${BASE_URL}/clubs/${clubId}/players/${userId}/${path}`,
            success(r) {
              const list = r.data || [];
              list.forEach(rec => {
                const d = rec.self_delta;
                if (d != null) {
                  const abs = Math.abs(d).toFixed(3);
                  rec.deltaDisplay =
                    (d > 0 ? '+' : d < 0 ? '-' : '') + abs;
                  rec.deltaClass = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
                } else {
                  rec.deltaDisplay = '';
                  rec.deltaClass = 'neutral';
                }
                if (rec.self_rating_after != null)
                  rec.self_rating_after = rec.self_rating_after.toFixed(3);
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
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches`,
      data: { token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '加载失败', icon: 'none' });
          return;
        }
        const uid = that.data.userId;
        const isAdmin = that.data.isAdmin;
        const list = res.data.map(it => {
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.status = it.display_status_text || '';
          const isParticipant = it.player_a === uid || it.player_b === uid;
          it.canApprove = isAdmin && it.confirmed_a && it.confirmed_b;
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
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '加载失败', icon: 'none' });
          return;
        }
        const uid = that.data.userId;
        const isAdmin = that.data.isAdmin;
        const list = res.data.map(it => {
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.status = it.display_status_text || '';
          const participants = [it.a1, it.a2, it.b1, it.b2];
          it.canApprove = isAdmin && it.confirmed_a && it.confirmed_b;
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
