const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {},
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
            if (resp.statusCode === 200 && resp.data.token) {
              wx.setStorageSync('token', resp.data.token);
              wx.setStorageSync('user_id', resp.data.user_id);
              wx.navigateTo({ url: '/pages/editprofile/editprofile' });
            } else {
              wx.showToast({ title: '失败', icon: 'none' });
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
