const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const store = require('../../store/store');

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
    const clubId = store.clubId;
    const raterId = store.userId;
    const token = store.token;
    const rating = parseFloat(this.data.rating);
    const targetId = this.data.targetId;
    const that = this;
    if (!clubId || !raterId || !token || !targetId || isNaN(rating)) return;
    request({
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
    const clubId = store.clubId;
    const that = this;
    if (!clubId || !id) return;
    request({
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
