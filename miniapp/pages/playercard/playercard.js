const BASE_URL = getApp().globalData.BASE_URL;
const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');

function calcAge(birth) {
  const d = new Date(birth);
  if (isNaN(d)) return '';
  const diff = Date.now() - d.getTime();
  return Math.floor(diff / (365 * 24 * 60 * 60 * 1000));
}

function genderText(g) {
  if (!g) return '';
  if (g === 'M' || g === 'Male' || g === '男') return '男';
  if (g === 'F' || g === 'Female' || g === '女') return '女';
  return g;
}

function formatExtraLines(info) {
  const line1 = [];
  const gender = genderText(info.gender);
  if (gender) line1.push(gender);
  const age = calcAge(info.birth);
  if (age) line1.push(`${age}岁`);

  const line2 = [];
  if (info.handedness) line2.push(info.handedness);
  if (info.backhand) line2.push(info.backhand);

  return { line1: line1.join('·'), line2: line2.join('·') };
}

Page({
  data: {
    user: null,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    infoLine1: '',
    infoLine2: '',
    viewId: ''
  },
  onLoad(options) {
    this.setData({ viewId: options && options.uid ? options.uid : wx.getStorageSync('user_id') });
  },
  onShow() {
    this.loadUser();
  },
  loadUser() {
    const uid = this.data.viewId || wx.getStorageSync('user_id');
    if (!uid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/players/${uid}`,
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
        const extra = formatExtraLines(user);
        that.setData({
          user,
          infoLine1: extra.line1,
          infoLine2: extra.line2
        });
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
