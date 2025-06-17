const { observable } = require('mobx-miniprogram');

const store = observable({
  userId: '',
  token: '',
  refreshToken: '',
  clubId: '',
  userInfo: null,
  setAuth(token, userId, refreshToken) {
    this.token = token || '';
    this.userId = userId || '';
    this.refreshToken = refreshToken || '';
    if (token) wx.setStorageSync('token', token); else wx.removeStorageSync('token');
    if (userId) wx.setStorageSync('user_id', userId); else wx.removeStorageSync('user_id');
    if (refreshToken) wx.setStorageSync('refresh_token', refreshToken); else wx.removeStorageSync('refresh_token');
  },
  clearAuth() {
    this.token = '';
    this.userId = '';
    this.refreshToken = '';
    this.userInfo = null;
    this.clubId = '';
    wx.removeStorageSync('token');
    wx.removeStorageSync('user_id');
    wx.removeStorageSync('refresh_token');
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
