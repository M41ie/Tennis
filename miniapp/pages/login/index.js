const { hideKeyboard } = require('../../utils/hideKeyboard');
const userService = require('../../services/user');
const store = require('../../store/store');
const { t } = require('../../utils/locales');
const ensureSubscribe = require('../../utils/ensureSubscribe');

Page({
  data: { t },
  hideKeyboard,
  wechatLogin() {
    wx.login({
      success(res) {
        if (!res.code) return;
        userService
          .wechatLogin(res.code)
          .then(resp => {
            if (resp.access_token) {
              store.setAuth(resp.access_token, resp.user_id, resp.refresh_token);
              ensureSubscribe('club_join');
              ensureSubscribe('match');
              wx.navigateBack();
            } else {
              wx.showToast({ duration: 4000,  title: t.loginFailed, icon: 'none' });
            }
          })
          .catch(() => {});
      }
    });
  }
});
