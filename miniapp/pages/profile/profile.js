Page({
  data: {
    user: null,
    records: [],
    loginId: '',
    loginPw: '',
    isSelf: false,
    clubId: ''
  },
  onLoad(options) {
    const userId = options.id || wx.getStorageSync('user_id');
    const cid = options.cid || wx.getStorageSync('club_id');
    if (userId && cid) {
      this.setData({ clubId: cid, isSelf: userId === wx.getStorageSync('user_id') });
      this.fetchUser(cid, userId);
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
    const userId = wx.getStorageSync('user_id');
    if (!userId) return;
    const that = this;
    wx.request({
      url: 'http://localhost:8000/clubs',
      success(res) {
        if (res.data.length > 0) {
          const cid = res.data[0].club_id;
          const token = wx.getStorageSync('token');
          wx.request({
            url: `http://localhost:8000/clubs/${cid}/join`,
            method: 'POST',
            data: { user_id: userId, token },
            success() {
              wx.setStorageSync('club_id', cid);
              wx.showToast({ title: 'Joined ' + cid, icon: 'none' });
              that.setData({ clubId: cid, isSelf: true });
              that.fetchUser(cid, userId);
            }
          });
        }
      }
    });
  },
  manageMembers() {
    wx.navigateTo({ url: '/pages/manage/manage' });
  },
  toPrerate() {
    wx.navigateTo({ url: '/pages/prerate/prerate' });
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
});
