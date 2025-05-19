Page({
  data: {
    user: null
  },
  onLoad(options) {
    const userId = options.id || wx.getStorageSync('user_id');
    if (userId) {
      this.fetchUser(userId);
    }
  },
  login() {
    wx.showToast({ title: 'Login not implemented', icon: 'none' });
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
    wx.showToast({ title: 'Club management not implemented', icon: 'none' });
  }
});
