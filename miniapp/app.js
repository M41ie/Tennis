const { BASE_URL } = require('./config');
const store = require('./store/store');
const { zh_CN: t } = require('./utils/locales');

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
    store.setAuth(
      wx.getStorageSync('token'),
      wx.getStorageSync('user_id'),
      wx.getStorageSync('refresh_token')
    );
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
          wx.showToast({ duration: 4000,  title: t.networkError, icon: 'none' });
        }
      });
    }
  }
});

module.exports = {
  BASE_URL
};
