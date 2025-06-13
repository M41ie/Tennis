const { hideKeyboard } = require('../../utils/hideKeyboard');
const userService = require('../../services/user');

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
    userService
      .login(this.data.loginId, this.data.loginPw)
      .then(res => {
        if (res.success) {
          wx.setStorageSync('token', res.token);
          wx.setStorageSync('user_id', res.user_id || this.data.loginId);
          wx.navigateBack();
        } else {
          wx.showToast({ title: '登录失败', icon: 'none' });
        }
      })
      .catch(() => {});
  },
  hideKeyboard,
  wechatLogin() {
    wx.login({
      success(res) {
        if (!res.code) return;
        userService
          .wechatLogin(res.code)
          .then(resp => {
            if (resp.token) {
              wx.setStorageSync('token', resp.token);
              wx.setStorageSync('user_id', resp.user_id);
              wx.navigateBack();
            } else {
              wx.showToast({ title: '登录失败', icon: 'none' });
            }
          })
          .catch(() => {});
      }
    });
  },
  toRegister() {
    wx.navigateTo({ url: '/pages/register/register' });
  }
});
