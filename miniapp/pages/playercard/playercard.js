const BASE_URL = getApp().globalData.BASE_URL;
const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');

function calcAge(birth) {
  const d = new Date(birth);
  if (isNaN(d)) return '';
  const diff = Date.now() - d.getTime();
  return Math.floor(diff / (365 * 24 * 60 * 60 * 1000));
}

function formatExtra(info) {
  const parts = [];
  if (info.gender) parts.push(info.gender);
  const age = calcAge(info.birth);
  if (age) parts.push(`${age}岁`);
  if (info.handedness) parts.push(info.handedness);
  if (info.backhand) parts.push(info.backhand);
  return parts.join('·');
}

Page({
  data: {
    user: null,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    extraInfo: ''
  },
  onShow() {
    this.loadUser();
  },
  loadUser() {
    const uid = wx.getStorageSync('user_id');
    const cid = wx.getStorageSync('club_id');
    if (!uid || !cid) return;
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
          gender: raw.gender,
          birth: raw.birth,
          handedness: raw.handedness,
          backhand: raw.backhand,
          rating_singles: formatRating(raw.rating_singles ?? raw.singles_rating),
          rating_doubles: formatRating(raw.rating_doubles ?? raw.doubles_rating),
          weighted_games_singles: typeof singlesCount === 'number'
            ? singlesCount.toFixed(2)
            : (singlesCount ? Number(singlesCount).toFixed(2) : '--'),
          weighted_games_doubles: typeof doublesCount === 'number'
            ? doublesCount.toFixed(2)
            : (doublesCount ? Number(doublesCount).toFixed(2) : '--')
        };
        that.setData({ user, extraInfo: formatExtra(user) });
      }
    });
  },
  editProfile() {
    wx.navigateTo({ url: '/pages/editprofile/editprofile' });
  },
  onShareAppMessage() {
    return {
      title: `${this.data.user.name} 球员卡`,
      path: '/pages/playercard/playercard'
    };
  }
});
