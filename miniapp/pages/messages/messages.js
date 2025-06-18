const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {
    list: []
  },
  hideKeyboard,
  onShow() {
    const uid = store.userId;
    const token = store.token;
    const that = this;
    if (!uid || !token) return;
    request({
      url: `${BASE_URL}/users/${uid}/messages?token=${token}`,
      success(res) {
        that.setData({ list: res.data });
      }
    });
  },
  markRead(e) {
    const idx = e.currentTarget.dataset.index;
    const uid = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/users/${uid}/messages/${idx}/read`,
      method: 'POST',
      data: { token },
      success() {
        const list = that.data.list.slice();
        if (list[idx]) list[idx].read = true;
        that.setData({ list });
        request({
          url: `${BASE_URL}/users/${uid}/messages/unread_count?token=${token}`,
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
