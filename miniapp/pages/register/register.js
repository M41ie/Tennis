const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
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
        request({
          url: `${BASE_URL}/wechat_login`,
          method: 'POST',
          data: { code: res.code },
          timeout: 5000,
          success(resp) {
            if (resp.statusCode === 200 && resp.data.access_token) {
              store.setAuth(
                resp.data.access_token,
                resp.data.user_id,
                resp.data.refresh_token
              );
              ensureSubscribe('club_join');
              ensureSubscribe('match');
              wx.navigateTo({ url: '/pages/editprofile/editprofile' });
            } else {
              wx.showToast({ duration: 4000,  title: t.failed, icon: 'none' });
            }
          },
          fail() {
            wx.showToast({ duration: 4000,  title: t.networkError, icon: 'none' });
          }
        });
      }
    });
  }
});
