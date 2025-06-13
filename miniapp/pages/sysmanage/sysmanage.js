const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    currentTab: 0,
    userQuery: '',
    clubQuery: '',
    totalUsers: '--',
    totalMatches: '--',
    totalClubs: '--',
    pendingItems: '--',
    topClubs: []
  },
  onLoad() {
    this.loadStats();
    this.loadClubStats();
  },
  loadStats() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/sys/stats`,
      success(res) {
        const d = res.data || {};
        that.setData({
          totalUsers: d.total_users != null ? d.total_users : '--',
          totalMatches: d.total_matches != null ? d.total_matches : '--',
          totalClubs: d.total_clubs != null ? d.total_clubs : '--',
          pendingItems: d.pending_items != null ? d.pending_items : '--'
        });
      }
    });
  },
  loadClubStats() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/sys/clubs`,
      success(res) {
        const list = res.data || [];
        list.sort((a, b) => (b.total_matches || 0) - (a.total_matches || 0));
        const top = list.slice(0, 10);
        if (!top.length) {
          that.setData({ topClubs: [] });
          return;
        }
        const result = [];
        let count = 0;
        top.forEach(c => {
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
                doubles_avg: doublesAvg,
                total_matches: c.total_matches,
                pending_members: c.pending_members
              });
            },
            complete() {
              count++;
              if (count === top.length) {
                result.sort(
                  (a, b) => (b.total_matches || 0) - (a.total_matches || 0)
                );
                that.setData({ topClubs: result });
              }
            }
          });
        });
      }
    });
  },
  switchTab(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ currentTab: idx });
  },
  onUserInput(e) { this.setData({ userQuery: e.detail.value }); },
  onClubInput(e) { this.setData({ clubQuery: e.detail.value }); },
  searchUsers() {
    const q = this.data.userQuery.trim();
    const url = q ? `/pages/sys-user-list/index?query=${q}` : '/pages/sys-user-list/index';
    wx.navigateTo({ url });
  },
  searchClubs() {
    const q = this.data.clubQuery.trim();
    const url = q ? `/pages/sys-club-list/index?query=${q}` : '/pages/sys-club-list/index';
    wx.navigateTo({ url });
  },
  openAllUsers() {
    wx.navigateTo({ url: '/pages/sys-user-list/index' });
  },
  openAllMatches() {
    wx.navigateTo({ url: '/pages/sys-match-list/index' });
  },
  openClub(e) {
    const cid = e.currentTarget.dataset.id;
    if (!cid) return;
    wx.navigateTo({ url: `/pages/manage/manage?cid=${cid}` });
  }
});
