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
    wx.request({
      url: 'http://localhost:8000/users',
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
          url: 'http://localhost:8000/wechat_login',
          method: 'POST',
          data: { code: res.code },
          success(resp) {
            if (resp.statusCode === 200 && resp.data.token) {
              wx.setStorageSync('token', resp.data.token);
              wx.setStorageSync('user_id', resp.data.user_id);
              wx.navigateBack();
            } else {
              wx.showToast({ title: 'Failed', icon: 'none' });
            }
          }
        });
      }
    });
  }
});
