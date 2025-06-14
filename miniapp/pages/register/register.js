const BASE_URL = getApp().globalData.BASE_URL;
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {
    name: '',
    password: ''
  },
  onName(e) { this.setData({ name: e.detail.value }); },
  onPassword(e) { this.setData({ password: e.detail.value }); },
  register() {
    if (!this.data.name || !this.data.password) {
      wx.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }
    const nameOk = /^[A-Za-z\u4e00-\u9fa5]{1,12}$/.test(this.data.name);
    if (!nameOk) {
      wx.showToast({ title: '用户名仅支持中英文，且不能超过12字符', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
      url: `${BASE_URL}/users`,
      method: 'POST',
      data: {
        name: this.data.name,
        password: this.data.password
      },
      success(res) {
        if (res.statusCode === 200 && res.data.user_id) {
          const uid = res.data.user_id;
          wx.request({
            url: `${BASE_URL}/login`,
            method: 'POST',
            data: { user_id: uid, password: that.data.password },
            success(r2) {
              if (r2.data.success) {
                wx.setStorageSync('token', r2.data.token);
                wx.setStorageSync('user_id', uid);
                wx.showToast({ title: '注册成功', icon: 'success' });
                wx.navigateTo({ url: '/pages/editprofile/editprofile' });
              } else {
                wx.showToast({ title: '请稍后登录', icon: 'none' });
                wx.navigateBack();
              }
            },
            fail() {
              wx.showToast({ title: '网络错误', icon: 'none' });
            }
          });
        } else {
          wx.showToast({ title: '失败', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
  },
  hideKeyboard,
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
