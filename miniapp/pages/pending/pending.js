const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    singles: [],
    doubles: [],
    userId: ''
  },
  onLoad() {
    this.setData({ userId: wx.getStorageSync('user_id') });
    this.fetchPendings();
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
        const uid = that.data.userId;
        const list = res.data.map(it => {
          const isA = it.player_a === uid;
          const isB = it.player_b === uid;
          const isParticipant = isA || isB;
          const confirmedSelf = (isA && it.confirmed_a) || (isB && it.confirmed_b);
          const confirmedOpp = (isA && it.confirmed_b) || (isB && it.confirmed_a);
          it.canConfirm = isParticipant && !confirmedSelf;
          it.canReject = isParticipant && !confirmedSelf;
          it.canApprove = !isParticipant && it.confirmed_a && it.confirmed_b;
          if (isParticipant && confirmedSelf && !confirmedOpp) {
            it.status = 'Waiting for opponent';
          } else if (it.confirmed_a && it.confirmed_b) {
            it.status = 'Pending approval';
          } else {
            it.status = '';
          }
          return it;
        });
        that.setData({ singles: list });
      }
    });
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles`,
      data: { token },
      success(res) {
        const uid = that.data.userId;
        const list = res.data.map(it => {
          const participants = [it.a1, it.a2, it.b1, it.b2];
          const isParticipant = participants.includes(uid);
          let confirmedSelf = false;
          if (uid === it.a1 || uid === it.a2) confirmedSelf = it.confirmed_a;
          if (uid === it.b1 || uid === it.b2) confirmedSelf = it.confirmed_b;
          const confirmedOpp =
            (uid === it.a1 || uid === it.a2) ? it.confirmed_b : it.confirmed_a;
          it.canConfirm = isParticipant && !confirmedSelf;
          it.canReject = isParticipant && !confirmedSelf;
          it.canApprove = !isParticipant && it.confirmed_a && it.confirmed_b;
          if (isParticipant && confirmedSelf && !confirmedOpp) {
            it.status = 'Waiting for opponent';
          } else if (it.confirmed_a && it.confirmed_b) {
            it.status = 'Pending approval';
          } else {
            it.status = '';
          }
          return it;
        });
        that.setData({ doubles: list });
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
      complete() { that.fetchPendings(); }
    });
  }
});
