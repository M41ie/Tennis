const BASE_URL = getApp().globalData.BASE_URL;
const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');

Page({
  data: {
    loggedIn: false,
    user: null,
    clubId: '',
    joinedClubs: [],
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    iconClub: IMAGES.ICON_CLUB,
    iconComing: IMAGES.ICON_COMING,
    myClubBtnText: '我的俱乐部'
  },
  onShow() {
    const uid = wx.getStorageSync('user_id');
    const cid = wx.getStorageSync('club_id');
    if (uid) {
      this.setData({ loggedIn: true });
      this.loadJoinedClubs(uid, cid);
    } else {
      this.setData({ loggedIn: false, user: null });
    }
  },
  loadJoinedClubs(uid, cid) {
    const that = this;
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const list = res.data.joined_clubs || [];
        let current = cid;
        if (!current && list.length) {
          current = list[0];
          wx.setStorageSync('club_id', current);
        }
        that.setData({
          joinedClubs: list,
          clubId: current || '',
          myClubBtnText: list.length ? '我的俱乐部' : '加入俱乐部'
        });
        if (current) that.loadUser(current, uid);
      }
    });
  },
  loadUser(cid, uid) {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${uid}`,
      success(res) {
        const data = res.data || {};
        data.rating_singles = formatRating(data.rating_singles);
        data.rating_doubles = formatRating(data.rating_doubles);
        that.setData({ user: data });
      }
    });
  },
  editProfile() {
    wx.navigateTo({ url: '/pages/register/register?edit=true' });
  },
  toLogin() { wx.navigateTo({ url: '/pages/login/index' }); },
  toRegister() { wx.navigateTo({ url: '/pages/register/register' }); },
  goMyClub() {
    if (this.data.joinedClubs && this.data.joinedClubs.length) {
      wx.navigateTo({ url: '/pages/club-manage/index' });
    } else {
      wx.navigateTo({ url: '/pages/joinclub/joinclub' });
    }
  },
  logout() {
    const token = wx.getStorageSync('token');
    const that = this;
    const complete = function () {
      wx.removeStorageSync('token');
      wx.removeStorageSync('user_id');
      wx.removeStorageSync('club_id');
      that.setData({ loggedIn: false, user: null });
    };
    if (token) {
      wx.request({
        url: `${BASE_URL}/logout`,
        method: 'POST',
        data: { token },
        complete
      });
    } else {
      complete();
    }
  }
});
