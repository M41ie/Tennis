const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    pending: [],
    members: [],
    isAdmin: false,
    userId: '',
    clubName: '',
    clubSlogan: '',
    stats: {},
    role: '',
    roleText: ''
  },
  onLoad() {
    this.setData({ userId: wx.getStorageSync('user_id') });
    this.fetchClub();
    this.fetchPlayers();
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
        let role = 'member';
        if (info.leader_id === that.data.userId) role = 'leader';
        else if (info.admin_ids && info.admin_ids.includes(that.data.userId)) role = 'admin';
        const roleText = role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员';
        that.setData({
          pending: info.pending_members || [],
          isAdmin,
          clubName: info.name || '',
          clubSlogan: info.slogan || '',
          stats: info.stats || {},
          role,
          roleText
        });
      }
    });
  },
  fetchPlayers() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players`,
      success(res) {
        const list = res.data || [];
        list.forEach(p => {
          if (p.rating != null) p.rating = p.rating.toFixed(3);
          if (p.weighted_singles_matches != null) p.weighted_singles_matches = p.weighted_singles_matches.toFixed(2);
          if (p.weighted_doubles_matches != null) p.weighted_doubles_matches = p.weighted_doubles_matches.toFixed(2);
        });
        that.setData({ members: list });
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
  },
  viewPlayer(e) {
    const uid = e.currentTarget.dataset.uid;
    wx.navigateTo({ url: '/pages/playercard/playercard?uid=' + uid });
  },
  quitClub() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'quit' },
      complete() { wx.navigateBack(); }
    });
  },
  resignAdmin() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'resign_admin' },
      complete() { that.fetchClub(); }
    });
  },
  toggleAdmin() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'toggle_admin' },
      complete() { that.fetchClub(); }
    });
  },
  transferLeader() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'transfer_leader' },
      complete() { that.fetchClub(); }
    });
  }
});
