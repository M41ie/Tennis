const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    pending: [],
    members: [],
    isAdmin: false,
    userId: '',
    clubName: '',
    clubSlogan: ''
  },
  onLoad() {
    this.setData({ userId: wx.getStorageSync('user_id') });
    this.fetchClub();
  },
  fetchClub() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data;
        const isAdmin = info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId));
        that.setData({
          pending: info.pending_members || [],
          members: info.members || [],
          isAdmin,
          clubName: info.name || '',
          clubSlogan: info.slogan || ''
        });
      }
    });
  },
  approve(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/approve`,
      method: 'POST',
      data: { approver_id: this.data.userId, user_id: uid, token },
      complete() { that.fetchClub(); }
    });
  },
  kick(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/members/${uid}`,
      method: 'DELETE',
      data: { remover_id: this.data.userId, token, ban: false },
      complete() { that.fetchClub(); }
    });
  },
  ban(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/members/${uid}`,
      method: 'DELETE',
      data: { remover_id: this.data.userId, token, ban: true },
      complete() { that.fetchClub(); }
    });
  }
});
