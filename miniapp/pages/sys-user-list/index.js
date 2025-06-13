const BASE_URL = getApp().globalData.BASE_URL;

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
    const q = this.data.query.trim();
    const that = this;
    let url = `${BASE_URL}/sys/users`;
    const params = [];
    if (q) params.push('query=' + encodeURIComponent(q));
    if (this.data.page > 1) params.push('page=' + this.data.page);
    if (params.length) url += '?' + params.join('&');
    wx.request({
      url,
      success(res) {
        const list = res.data || [];
        const users = that.data.page === 1 ? list : that.data.users.concat(list);
        that.setData({ users, finished: !list.length });
      }
    });
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
