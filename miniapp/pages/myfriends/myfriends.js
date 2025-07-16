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
        this.setData({ list: res || [], isLoading: false });
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
