Page({
  data: {
    user: null,
    records: [],
    loginId: '',
    loginPw: '',
    isSelf: false,
    clubId: '',
    joinedClubs: []
  },
  onLoad(options) {
    const userId = options.id || wx.getStorageSync('user_id');
    const cid = options.cid || wx.getStorageSync('club_id');
    if (userId) {
      this.setData({ isSelf: userId === wx.getStorageSync('user_id') });
      this.fetchJoined(userId, cid);
    }
  },
  onUserId(e) { this.setData({ loginId: e.detail.value }); },
  onPassword(e) { this.setData({ loginPw: e.detail.value }); },
  login() {
    const that = this;
    wx.request({
      url: 'http://localhost:8000/login',
      method: 'POST',
      data: { user_id: this.data.loginId, password: this.data.loginPw },
      success(res) {
        if (res.data.success) {
          wx.setStorageSync('token', res.data.token);
          wx.setStorageSync('user_id', that.data.loginId);
          const cid = wx.getStorageSync('club_id');
          if (cid) {
            that.setData({ isSelf: true, clubId: cid });
            that.fetchUser(cid, that.data.loginId);
          }
        } else {
          wx.showToast({ title: 'Login failed', icon: 'none' });
        }
      }
    });
  },
  fetchUser(cid, id) {
    const that = this;
    wx.request({
      url: `http://localhost:8000/clubs/${cid}/players/${id}?recent=5`,
      success(res) {
        that.setData({ user: res.data, records: res.data.recent_records || [] });
      }
    });
  },
  manageClubs() {
    wx.navigateTo({ url: '/pages/joinclub/joinclub' });
  },
  toRegister() {
    wx.navigateTo({ url: '/pages/register/register' });
  },
  manageClubs() {
    wx.navigateTo({ url: '/pages/joinclub/joinclub' });
  },
  toRegister() {
    wx.navigateTo({ url: '/pages/register/register' });
  },
  manageMembers() {
    wx.navigateTo({ url: '/pages/manage/manage' });
  },
  viewMessages() {
    wx.navigateTo({ url: '/pages/messages/messages' });
  },
  toPrerate() {
    wx.navigateTo({ url: '/pages/prerate/prerate' });
  },
  selectClub(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    if (cid && uid) {
      wx.setStorageSync('club_id', cid);
      this.setData({ clubId: cid });
      this.fetchUser(cid, uid);
    }
  },
  logout() {
    const token = wx.getStorageSync('token');
    const that = this;
    if (token) {
      wx.request({
        url: 'http://localhost:8000/logout',
        method: 'POST',
        data: { token },
        complete() {
          wx.removeStorageSync('token');
          wx.removeStorageSync('user_id');
          wx.removeStorageSync('club_id');
          that.setData({ user: null, loginId: '', loginPw: '' });
        }
      });
    } else {
      wx.removeStorageSync('token');
      wx.removeStorageSync('user_id');
      wx.removeStorageSync('club_id');
      this.setData({ user: null, loginId: '', loginPw: '' });
    }
  }
  ,openDetail(e) {
    const rec = this.data.records[e.currentTarget.dataset.index];
    wx.navigateTo({
      url:
        '/pages/recorddetail/recorddetail?data=' +
        encodeURIComponent(JSON.stringify(rec))
    });
  }
});
