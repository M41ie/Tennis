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
        wx.request({
          url: `http://localhost:8000/users/${uid}/messages/unread_count?token=${token}`,
          success(res2) {
            const pages = getCurrentPages();
            if (pages.length > 1) {
              const prev = pages[pages.length - 2];
              if (prev && prev.setData) {
                prev.setData({ unreadCount: res2.data.unread });
              }
            }
          }
        });
      }
    });
  }
});
