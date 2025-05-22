Page({
  data: {
    user: null,
    loginId: '',
    loginPw: ''
  },
  onLoad(options) {
    const userId = options.id || wx.getStorageSync('user_id');
    if (userId) {
      this.fetchUser(userId);
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
          that.fetchUser(that.data.loginId);
        } else {
          wx.showToast({ title: 'Login failed', icon: 'none' });
        }
      }
    });
  },
  fetchUser(id) {
    const clubId = wx.getStorageSync('club_id');
    if (!clubId) return;
    const that = this;
    wx.request({
      url: `http://localhost:8000/clubs/${clubId}/players`,
      success(res) {
        const user = res.data.find(p => p.user_id === id);
        if (user) {
          that.setData({ user });
        }
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
              that.fetchUser(userId);
            }
          });
        }
      }
    });
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
