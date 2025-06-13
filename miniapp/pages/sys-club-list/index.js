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
    // TODO: call backend API to load clubs
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
  }
});
