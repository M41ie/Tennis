Page({
  data: {
    list: []
  },
  onShow() {
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!uid || !token) return;
    wx.request({
      url: `http://localhost:8000/users/${uid}/messages?token=${token}`,
      success(res) {
        that.setData({ list: res.data });
      }
    });
  },
  markRead(e) {
    const idx = e.currentTarget.dataset.index;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `http://localhost:8000/users/${uid}/messages/${idx}/read`,
      method: 'POST',
      data: { token },
      success() {
        const list = that.data.list.slice();
        if (list[idx]) list[idx].read = true;
        that.setData({ list });
      }
    });
  }
});
