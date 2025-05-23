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
  }
});
