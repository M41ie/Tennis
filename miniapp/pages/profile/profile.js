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
          wx.request({
            url: `http://localhost:8000/clubs/${cid}/join`,
            method: 'POST',
            data: { user_id: userId },
            success() {
              wx.setStorageSync('club_id', cid);
              wx.showToast({ title: 'Joined ' + cid, icon: 'none' });
              that.fetchUser(userId);
            }
          });
        }
      }
    });
  }
});
