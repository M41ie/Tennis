const friendService = require('../../services/friend');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { t } = require('../../utils/locales');
const { withBase } = require('../../utils/format');
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
            const winRate = item.singles_weight ? ((item.singles_wins || 0) / item.singles_weight * 100).toFixed(1) : 0;
            item.matches_singles = { count: item.singles_weight, win_rate: winRate };
          }
          if (!item.matches_doubles && item.doubles_weight !== undefined) {
            const winRate = item.doubles_weight ? ((item.doubles_wins || 0) / item.doubles_weight * 100).toFixed(1) : 0;
            item.matches_doubles = { count: item.doubles_weight, win_rate: winRate };
          }
          if (!item.matches_against && item.weight !== undefined) {
            const winRate = item.weight ? ((item.wins || 0) / item.weight * 100).toFixed(1) : 0;
            item.matches_against = { count: item.weight, win_rate: winRate };
          }
          if (!item.matches_partnered && item.partner_games !== undefined) {
            const winRate = item.partner_games ? ((item.partner_wins || 0) / item.partner_games * 100).toFixed(1) : 0;
            item.matches_partnered = { count: item.partner_games, win_rate: winRate };
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
