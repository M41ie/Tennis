const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    userId: '',
    name: '',
    password: ''
  },
  onUserId(e) { this.setData({ userId: e.detail.value }); },
  onName(e) { this.setData({ name: e.detail.value }); },
  onPassword(e) { this.setData({ password: e.detail.value }); },
  register() {
    if (!this.data.userId || !this.data.name || !this.data.password) {
      wx.showToast({ title: '信息不完整', icon: 'none' });
      return;
    }
    wx.request({
      url: `${BASE_URL}/users`,
      method: 'POST',
      data: {
        user_id: this.data.userId,
        name: this.data.name,
        password: this.data.password
      },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ title: 'Registered', icon: 'success' });
          wx.navigateBack();
        } else {
          wx.showToast({ title: 'Failed', icon: 'none' });
        }
      }
    });
  },
  wechatLogin() {
    wx.login({
      success(res) {
        if (!res.code) return;
        wx.request({
          url: `${BASE_URL}/wechat_login`,
          method: 'POST',
          data: { code: res.code },
          timeout: 5000,
          success(resp) {
            if (resp.statusCode === 200 && resp.data.token) {
              wx.setStorageSync('token', resp.data.token);
              wx.setStorageSync('user_id', resp.data.user_id);
              wx.navigateBack();
            } else {
              wx.showToast({ title: 'Failed', icon: 'none' });
            }
          },
          fail() {
            wx.showToast({ title: '网络错误', icon: 'none' });
          }
        });
      }
    });
  }
});
