Page({
  data: {
    targetId: '',
    rating: '',
    target: null
  },
  onTarget(e) { this.setData({ targetId: e.detail.value }); },
  onRating(e) { this.setData({ rating: e.detail.value }); },
  submit() {
    const clubId = wx.getStorageSync('club_id');
    const raterId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const rating = parseFloat(this.data.rating);
    const targetId = this.data.targetId;
    const that = this;
    if (!clubId || !raterId || !token || !targetId || isNaN(rating)) return;
    wx.request({
      url: `http://localhost:8000/clubs/${clubId}/prerate`,
      method: 'POST',
      data: { rater_id: raterId, target_id: targetId, rating, token },
      success() {
        wx.showToast({ title: 'Submitted', icon: 'success' });
        that.fetchTarget(targetId);
      }
    });
  },
  fetchTarget(id) {
    const clubId = wx.getStorageSync('club_id');
    const that = this;
    if (!clubId || !id) return;
    wx.request({
      url: `http://localhost:8000/clubs/${clubId}/players/${id}`,
      success(res) { that.setData({ target: res.data }); }
    });
  }
});
