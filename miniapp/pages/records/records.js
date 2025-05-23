Page({
  data: {
    records: [],
    doubles: false
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
          const path = that.data.doubles ? 'doubles_records' : 'records';
          wx.request({
            url: `http://localhost:8000/clubs/${clubId}/players/${userId}/${path}`,
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
  },
  addMatch() {
    wx.navigateTo({ url: '/pages/addmatch/addmatch' });
  },
  viewPending() {
    wx.navigateTo({ url: '/pages/pending/pending' });
  }
});
