const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const store = require('../../store/store');
const { t } = require('../../utils/locales');

Page({
  data: { t },
  hideKeyboard,
  async wechatLogin() {
    try {
      const res = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });
      if (!res.code) return;
      const resp = await request({
        url: `${BASE_URL}/wechat_login`,
        method: 'POST',
        data: { code: res.code },
        timeout: 5000
      });
      if (resp.access_token) {
        store.setAuth(resp.access_token, resp.user_id, resp.refresh_token);
        wx.navigateTo({ url: '/pages/editprofile/editprofile' });
      } else {
        wx.showToast({ duration: 4000, title: t.failed, icon: 'none' });
      }
    } catch (e) {
      wx.showToast({ duration: 4000, title: t.networkError, icon: 'none' });
    }
  }
});
