Page({
  data: {
    records: []
  },
  onLoad() {
    this.fetchRecords();
  },
  fetchRecords() {
    const userId = wx.getStorageSync('user_id');
    const clubId = wx.getStorageSync('club_id');
    const that = this;
    if (!userId || !clubId) return;
    wx.request({
      url: `http://localhost:8000/clubs/${clubId}/players`,
      success(res) {
        const player = res.data.find(p => p.user_id === userId);
        if (player) {
          wx.request({
            url: `http://localhost:8000/clubs/${clubId}/players/${userId}/records`,
            success(r) { that.setData({ records: r.data }); }
          });
        }
      }
    });
  },
  viewRecord(e) {
    const rec = this.data.records[e.currentTarget.dataset.index];
    wx.showModal({
      title: 'Match Detail',
      content: JSON.stringify(rec),
      showCancel: false
    });
  }
});
