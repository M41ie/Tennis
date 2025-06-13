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
        if (!list.length) {
          that.setData({ clubs: [], finished: true });
          return;
        }
        const result = [];
        let count = 0;
        list.forEach(c => {
          wx.request({
            url: `${BASE_URL}/clubs/${c.club_id}`,
            success(r) {
              const info = r.data || {};
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
              result.push({
                club_id: c.club_id,
                name: c.name,
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
              });
            },
            complete() {
              count++;
              if (count === list.length) {
                const clubs =
                  that.data.page === 1
                    ? result
                    : that.data.clubs.concat(result);
                that.setData({ clubs, finished: true });
              }
            }
          });
        });
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
