const friendService = require('../../services/friend');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { t } = require('../../utils/locales');

Page({
  data: {
    t,
    list: [],
    isLoading: true,
    isError: false
  },
  hideKeyboard,
  onShow() {
    const uid = store.userId;
    if (!uid) return;
    this.setData({ isLoading: true, isError: false });
    friendService.getFriends(uid)
      .then(res => {
        const list = (res || []).map(item => {
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
        this.setData({ list, isLoading: false });
      })
      .catch(() => {
        this.setData({ isError: true, isLoading: false });
      });
  },
  viewFriend(e) {
    const uid = e.currentTarget.dataset.uid;
    wx.navigateTo({ url: `/pages/playercard/playercard?uid=${uid}` });
  }
});
