const { hideKeyboard } = require('../../utils/hideKeyboard');
const userService = require('../../services/user');
const store = require('../../store/store');

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
              store.setAuth(resp.token, resp.user_id);
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
