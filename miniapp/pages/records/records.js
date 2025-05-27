const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    records: [],
    doubles: false,
    modeOptions: ['Singles', 'Doubles'],
    modeIndex: 0
  },
  onLoad() {
    this.fetchRecords();
  },
  onModeChange(e) {
    const idx = e.detail.value;
    this.setData({ modeIndex: idx, doubles: idx == 1 });
    this.fetchRecords();
  },
  fetchRecords() {
    const userId = wx.getStorageSync('user_id');
    const clubId = wx.getStorageSync('club_id');
    const that = this;
    if (!userId || !clubId) return;
    wx.request({
      url: `${BASE_URL}/clubs/${clubId}/players`,
      success(res) {
        const player = res.data.find(p => p.user_id === userId);
        if (player) {
          const path = that.data.doubles ? 'doubles_records' : 'records';
          wx.request({
            url: `${BASE_URL}/clubs/${clubId}/players/${userId}/${path}`,
            success(r) {
              const list = r.data || [];
              list.forEach(rec => {
                const d = rec.self_delta;
                if (d != null) {
                  const abs = Math.abs(d).toFixed(3);
                  rec.deltaDisplay =
                    (d > 0 ? '+' : d < 0 ? '-' : '') + abs;
                  rec.deltaClass = d > 0 ? 'pos' : d < 0 ? 'neg' : 'neutral';
                } else {
                  rec.deltaDisplay = '';
                  rec.deltaClass = 'neutral';
                }
              });
              that.setData({ records: list });
            }
          });
        }
      }
    });
  },
  viewRecord(e) {
    const rec = this.data.records[e.currentTarget.dataset.index];
    wx.navigateTo({
      url:
        '/pages/recorddetail/recorddetail?data=' +
        encodeURIComponent(JSON.stringify(rec))
    });
  },
  addMatch() {
    wx.navigateTo({ url: '/pages/addmatch/addmatch' });
  },
  viewPending() {
    wx.navigateTo({ url: '/pages/pending/pending' });
  }
});
