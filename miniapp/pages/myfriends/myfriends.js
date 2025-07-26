const friendService = require('../../services/friend');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { t } = require('../../utils/locales');
const { withBase, formatScoreDiff } = require('../../utils/format');
const IMAGES = require('../../assets/base64.js');

Page({
  data: {
    t,
    list: [],
    isLoading: true,
    isError: false,
    totalFriends: 0,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR
  },
  hideKeyboard,
  onShow() {
    const uid = store.userId;
    if (!uid) return;
    this.setData({ isLoading: true, isError: false });
    friendService.getFriends(uid)
      .then(res => {
        const list = (res || []).map(item => {
          item.avatar = withBase(item.avatar || item.avatar_url);
          if (!item.matches_singles && item.singles_weight !== undefined) {
            const info = formatScoreDiff(item.singles_score_diff);
            item.matches_singles = {
              count: item.singles_weight,
              display: info.display,
              cls: info.cls,
            };
          }
          if (!item.matches_doubles && item.doubles_weight !== undefined) {
            const info = formatScoreDiff(item.doubles_score_diff);
            item.matches_doubles = {
              count: item.doubles_weight,
              display: info.display,
              cls: info.cls,
            };
          }
          if (!item.matches_partnered && item.partner_games !== undefined) {
            const info = formatScoreDiff(item.partner_score_diff);
            item.matches_partnered = {
              count: item.partner_games,
              display: info.display,
              cls: info.cls,
            };
          }
          return item;
        });
        this.setData({ list, isLoading: false, totalFriends: list.length });
      })
      .catch(() => {
        this.setData({ isError: true, isLoading: false });
      });
  },
  viewFriend(e) {
    const uid = e.currentTarget.dataset.uid;
    wx.navigateTo({ url: `/pages/friendrecords/friendrecords?uid=${uid}` });
  }
});
