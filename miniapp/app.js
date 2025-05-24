App({
  globalData: {
    userId: null
  },
  onLaunch() {
    const token = wx.getStorageSync('token');
    const uid = wx.getStorageSync('user_id');
    if (token && uid) {
      const that = this;
      wx.request({
        url: 'http://localhost:8000/check_token',
        method: 'POST',
        data: { token },
        timeout: 5000,
        success(res) {
          if (res.statusCode === 200) {
            that.globalData.userId = uid;
          } else {
            wx.removeStorageSync('token');
            wx.removeStorageSync('user_id');
          }
        },
        fail() {
          wx.showToast({ title: '网络错误', icon: 'none' });
        }
      });
    }
  }
});
