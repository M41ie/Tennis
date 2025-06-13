const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    query: '',
    clubs: [],
    page: 1,
    finished: false
  },
  onLoad(options) {
    if (options && options.query) {
      this.setData({ query: options.query });
    }
    wx.setNavigationBarTitle({ title: '俱乐部搜索结果' });
    this.fetchClubs();
  },
  fetchClubs() {
    const q = this.data.query.trim();
    const that = this;
    let url = `${BASE_URL}/sys/clubs`;
    if (q) url += `?query=${encodeURIComponent(q)}`;
    wx.request({
      url,
      success(res) {
        const list = res.data || [];
        const clubs = that.data.page === 1 ? list : that.data.clubs.concat(list);
        that.setData({ clubs, finished: !list.length });
      }
    });
  },
  onPullDownRefresh() {
    this.setData({ page: 1, clubs: [], finished: false });
    this.fetchClubs();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchClubs();
  },
  openClub(e) {
    const cid = e.currentTarget.dataset.id;
    if (!cid) return;
    wx.navigateTo({ url: `/pages/manage/manage?cid=${cid}` });
  }
});
