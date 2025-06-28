const userService = require('../../services/user');
const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { formatExtraLines } = require('../../utils/userFormat');
const { t } = require('../../utils/locales');

Page({
  data: {
    t,
    user: null,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    infoLine1: '',
    infoLine2: '',
    viewId: '',
    isSelf: false
  },
  hideKeyboard,
  onLoad(options) {
    const viewId = options && options.uid ? options.uid : store.userId;
    this.setData({
      viewId,
      isSelf: viewId === store.userId
    });
  },
  onShow() {
    this.loadUser();
  },
  loadUser() {
    const uid = this.data.viewId || store.userId;
    if (!uid) return;
    const that = this;
    userService.getPlayerInfo(uid).then(raw => {
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
          singles_rating: formatRating(raw.singles_rating),
          doubles_rating: formatRating(raw.doubles_rating),
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
          infoLine2: extra.line2,
        });
        that.setData({
          isSelf: that.data.viewId === store.userId
        });
    });
  },
  editProfile() {
    wx.navigateTo({ url: '/pages/editprofile/editprofile' });
  },
  onShareAppMessage() {
    return {
      title: `${this.data.user.name} ${t.playerCard}`,
      path: `/pages/playercard/playercard?uid=${this.data.viewId}`
    };
  }
});
