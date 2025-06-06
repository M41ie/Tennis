const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    singles: [],
    doubles: [],
    userId: '',
    isAdmin: false
  },
  onLoad() {
    this.setData({ userId: wx.getStorageSync('user_id') });
    this.fetchClubInfo();
  },
  fetchClubInfo() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data;
        const admin = info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId));
        that.setData({ isAdmin: admin });
      },
      complete() { that.fetchPendings(); }
    });
  },
  fetchPendings() {
    const cid = wx.getStorageSync('club_id');
    const that = this;
    if (!cid) return;
    const token = wx.getStorageSync('token');
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches`,
      data: { token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: 'Failed to load', icon: 'none' });
          return;
        }
        const list = res.data.map(it => {
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.status = it.display_status_text || '';
          it.canApprove = it.can_approve;
          return it;
        });
        that.setData({ singles: list });
      },
      fail() {
        wx.showToast({ title: 'Request error', icon: 'none' });
      }
    });
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles`,
      data: { token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: 'Failed to load', icon: 'none' });
          return;
        }
        const list = res.data.map(it => {
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.status = it.display_status_text || '';
          it.canApprove = it.can_approve;
          return it;
        });
        that.setData({ doubles: list });
      },
      fail() {
        wx.showToast({ title: 'Request error', icon: 'none' });
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
          wx.showToast({ title: 'Error', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: 'Request error', icon: 'none' }); },
      complete() { that.fetchPendings(); }
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
          wx.showToast({ title: 'Error', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: 'Request error', icon: 'none' }); },
      complete() { that.fetchPendings(); }
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
          wx.showToast({ title: 'Error', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: 'Request error', icon: 'none' }); },
      complete() { that.fetchPendings(); }
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
          wx.showToast({ title: 'Error', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: 'Request error', icon: 'none' }); },
      complete() { that.fetchPendings(); }
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
          wx.showToast({ title: 'Error', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: 'Request error', icon: 'none' }); },
      complete() { that.fetchPendings(); }
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
          wx.showToast({ title: 'Error', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: 'Request error', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  }
});
