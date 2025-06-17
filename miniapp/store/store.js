const { observable } = require('mobx-miniprogram');

const store = observable({
  userId: '',
  token: '',
  clubId: '',
  userInfo: null,
  setAuth(token, userId) {
    this.token = token || '';
    this.userId = userId || '';
    if (token) wx.setStorageSync('token', token); else wx.removeStorageSync('token');
    if (userId) wx.setStorageSync('user_id', userId); else wx.removeStorageSync('user_id');
  },
  clearAuth() {
    this.token = '';
    this.userId = '';
    this.userInfo = null;
    this.clubId = '';
    wx.removeStorageSync('token');
    wx.removeStorageSync('user_id');
    wx.removeStorageSync('club_id');
  },
  setClubId(id) {
    this.clubId = id || '';
    if (id) wx.setStorageSync('club_id', id); else wx.removeStorageSync('club_id');
  },
  setUserInfo(info) {
    this.userInfo = info || null;
  }
});

module.exports = store;
