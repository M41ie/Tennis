const BASE_URL = getApp().globalData.BASE_URL;
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {
    targetId: '',
    rating: '',
    target: null
  },
  onTarget(e) { this.setData({ targetId: e.detail.value }); },
  onRating(e) { this.setData({ rating: e.detail.value }); },
  hideKeyboard,
  submit() {
    const clubId = wx.getStorageSync('club_id');
    const raterId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const rating = parseFloat(this.data.rating);
    const targetId = this.data.targetId;
    const that = this;
    if (!clubId || !raterId || !token || !targetId || isNaN(rating)) return;
    wx.request({
      url: `${BASE_URL}/clubs/${clubId}/prerate`,
      method: 'POST',
      data: { rater_id: raterId, target_id: targetId, rating, token },
      success() {
        wx.showToast({ title: '已提交', icon: 'success' });
        that.fetchTarget(targetId);
      }
    });
  },
  fetchTarget(id) {
    const clubId = wx.getStorageSync('club_id');
    const that = this;
    if (!clubId || !id) return;
    wx.request({
      url: `${BASE_URL}/clubs/${clubId}/players/${id}`,
      success(res) {
        const data = res.data;
        if (data.singles_rating != null)
          data.singles_rating = data.singles_rating.toFixed(3);
        if (data.doubles_rating != null)
          data.doubles_rating = data.doubles_rating.toFixed(3);
        that.setData({ target: data });
      }
    });
  }
});
