Page({
  data: {
    query: '',
    users: [],
    page: 1,
    finished: false
  },
  onLoad(options) {
    if (options && options.query) {
      this.setData({ query: options.query });
    }
    wx.setNavigationBarTitle({ title: '用户搜索结果' });
    this.fetchUsers();
  },
  fetchUsers() {
    // TODO: call backend API to load users
  },
  onPullDownRefresh() {
    this.setData({ page: 1, users: [], finished: false });
    this.fetchUsers();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchUsers();
  }
});
