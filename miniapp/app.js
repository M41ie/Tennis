const BASE_URL = 'http://localhost:8000';
const store = require('./store/store');

App({
  globalData: {
    userId: null,
    BASE_URL
  },
  onLaunch() {
    // inject Accept-Language header for all requests
    const origRequest = wx.request
    wx.request = function(options) {
      options = options || {}
      options.header = options.header || {}
      options.header['Accept-Language'] = 'zh-CN'
      return origRequest(options)
    }
    store.setAuth(wx.getStorageSync('token'), wx.getStorageSync('user_id'));
    store.setClubId(wx.getStorageSync('club_id'));
    if (store.token && store.userId) {
      const that = this;
      wx.request({
        url: `${BASE_URL}/check_token`,
        method: 'POST',
        data: { token: store.token },
        timeout: 5000,
        success(res) {
          if (res.statusCode === 200) {
            that.globalData.userId = store.userId;
          } else {
            store.clearAuth();
          }
        },
        fail() {
          wx.showToast({ title: '网络错误', icon: 'none' });
        }
      });
    }
  }
});

module.exports = {
  BASE_URL
};
