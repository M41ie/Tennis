const { hideKeyboard } = require('../../utils/hideKeyboard');
const userService = require('../../services/user');

Page({
  data: {},
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
  }
});
