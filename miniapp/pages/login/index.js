const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    loginId: '',
    loginPw: ''
  },
  onUserId(e) { this.setData({ loginId: e.detail.value }); },
  onPassword(e) { this.setData({ loginPw: e.detail.value }); },
  login() {
    if (!this.data.loginId || !this.data.loginPw) {
      wx.showToast({ title: '信息不完整', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
      url: `${BASE_URL}/login`,
      method: 'POST',
      data: { user_id: this.data.loginId, password: this.data.loginPw },
      timeout: 5000,
      success(res) {
        if (res.data.success) {
          wx.setStorageSync('token', res.data.token);
          wx.setStorageSync('user_id', that.data.loginId);
          wx.navigateBack();
        } else {
          wx.showToast({ title: '登录失败', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
  },
  wechatLogin() {
    const that = this;
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
              wx.showToast({ title: '登录失败', icon: 'none' });
            }
          },
          fail() {
            wx.showToast({ title: '网络错误', icon: 'none' });
          }
        });
      }
    });
  },
  toRegister() {
    wx.navigateTo({ url: '/pages/register/register' });
  }
});
