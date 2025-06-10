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
        const raw = res.data || {};
        const singlesCount = raw.weighted_games_singles ?? raw.weighted_singles_matches;
        const doublesCount = raw.weighted_games_doubles ?? raw.weighted_doubles_matches;
        const user = {
          id: raw.id || raw.user_id,
          avatar_url: raw.avatar_url || raw.avatar,
          name: raw.name,
          rating_singles: formatRating(raw.rating_singles ?? raw.singles_rating),
          rating_doubles: formatRating(raw.rating_doubles ?? raw.doubles_rating),
          weighted_games_singles: typeof singlesCount === 'number'
            ? singlesCount.toFixed(2)
            : (singlesCount ? Number(singlesCount).toFixed(2) : '--'),
          weighted_games_doubles: typeof doublesCount === 'number'
            ? doublesCount.toFixed(2)
            : (doublesCount ? Number(doublesCount).toFixed(2) : '--')
        };
        that.setData({ user });
      }
    });
  },
  editProfile() {
    wx.navigateTo({ url: '/pages/editprofile/editprofile' });
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
