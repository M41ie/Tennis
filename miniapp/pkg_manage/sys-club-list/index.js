const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {
    query: '',
    clubs: [],
    page: 1,
    finished: false
  },
  hideKeyboard,
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
    let url = `${BASE_URL}/clubs/search`;
    const limit = 20;
    const offset = (this.data.page - 1) * limit;
    const params = [];
    if (q) params.push(`query=${encodeURIComponent(q)}`);
    params.push('limit=' + limit);
    if (offset) params.push('offset=' + offset);
    if (params.length) url += '?' + params.join('&');
    request({
      url,
      success(res) {
        const list = res.data || [];
        if (!list.length) {
          if (that.data.page === 1) {
            that.setData({ clubs: [], finished: true });
          } else {
            that.setData({ finished: true });
          }
          return;
        }
        const result = list.map(info => {
          const stats = info.stats || {};
          const sr = stats.singles_rating_range || [];
          const dr = stats.doubles_rating_range || [];
          const fmt = n => (typeof n === 'number' ? n.toFixed(1) : '--');
          const singlesAvg =
            typeof stats.singles_avg_rating === 'number'
              ? fmt(stats.singles_avg_rating)
              : '--';
          const doublesAvg =
            typeof stats.doubles_avg_rating === 'number'
              ? fmt(stats.doubles_avg_rating)
              : '--';
          return {
            club_id: info.club_id,
            name: info.name,
            slogan: info.slogan || '',
            region: info.region || '',
            member_count: stats.member_count,
            singles_range: sr.length ? `${fmt(sr[0])}-${fmt(sr[1])}` : '--',
            doubles_range: dr.length ? `${fmt(dr[0])}-${fmt(dr[1])}` : '--',
            total_singles:
              stats.total_singles_matches != null
                ? stats.total_singles_matches.toFixed(0)
                : '--',
            total_doubles:
              stats.total_doubles_matches != null
                ? stats.total_doubles_matches.toFixed(0)
                : '--',
            singles_avg: singlesAvg,
            doubles_avg: doublesAvg
          };
        });
        if (that.data.page === 1) {
          that.setData({ clubs: result, finished: list.length < limit });
        } else {
          const start = that.data.clubs.length;
          const obj = { finished: list.length < limit };
          result.forEach((item, i) => {
            obj[`clubs[${start + i}]`] = item;
          });
          that.setData(obj);
        }
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
