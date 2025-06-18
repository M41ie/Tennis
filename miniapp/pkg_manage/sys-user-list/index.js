const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { formatRating, formatGames } = require('../../utils/format');
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {
    query: '',
    users: [],
    page: 1,
    finished: false,
    isLoading: true,
    isError: false,
    isEmpty: false
  },
  hideKeyboard,
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
    this.setData({ isLoading: this.data.page === 1, isError: false, isEmpty: false });
    let url = `${BASE_URL}/sys/users`;
    const params = [];
    const limit = 50;
    const offset = (this.data.page - 1) * limit;
    if (q) params.push('query=' + encodeURIComponent(q));
    params.push('limit=' + limit);
    if (offset) params.push('offset=' + offset);
    if (params.length) url += '?' + params.join('&');
    request({
      url,
      loading: false,
      success(res) {
        const raw = res.data || [];
        const list = raw.map(u => ({
          ...u,
          singles_rating: formatRating(u.singles_rating),
          doubles_rating: formatRating(u.doubles_rating),
          weighted_games_singles: formatGames(u.weighted_games_singles),
          weighted_games_doubles: formatGames(u.weighted_games_doubles)
        }));
        if (that.data.page === 1) {
          that.setData({
            users: list,
            finished: list.length < limit,
            isLoading: false,
            isEmpty: list.length === 0
          });
        } else {
          const start = that.data.users.length;
          const obj = { finished: list.length < limit, isLoading: false };
          list.forEach((item, i) => {
            obj[`users[${start + i}]`] = item;
          });
          that.setData(obj);
        }
      },
      fail() {
        that.setData({ isLoading: false, isError: true });
      }
    });
  },
  onPullDownRefresh() {
    this.setData({ page: 1, users: [], finished: false, isLoading: true, isError: false, isEmpty: false });
    this.fetchUsers();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchUsers();
  },
  openUser(e) {
    const uid = e.currentTarget.dataset.id;
    if (!uid) return;
    wx.navigateTo({ url: `/pkg_manage/sys-user-detail/index?user_id=${uid}` });
  }
});
