const BASE_URL = getApp().globalData.BASE_URL;
const { hideKeyboard } = require('../../utils/hideKeyboard');

Page({
  data: {
    currentTab: 0,
    userQuery: '',
    clubQuery: '',
    totalUsers: '--',
    totalMatches: '--',
    totalClubs: '--',
    pendingItems: '--',
    rankMode: 'matches',
    clubStatsRaw: [],
    topClubs: [],
    rankPage: 1,
    rankFinished: false,
    userDays: 7,
    matchDays: 7,
    userTrend: [],
    matchTrend: []
  },
  onLoad() {
    this.loadStats();
    this.loadClubStats();
    this.fetchUserTrend();
    this.fetchMatchActivity();
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
    const limit = 20;
    const offset = (this.data.rankPage - 1) * limit;
    wx.request({
      url: `${BASE_URL}/sys/clubs?limit=${limit}&offset=${offset}`,
      success(res) {
        const list = res.data || [];
        if (!list.length) {
          if (that.data.rankPage === 1) {
            that.setData({ clubStatsRaw: [], topClubs: [] });
          }
          that.setData({ rankFinished: true });
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
              if (count === list.length) {
                const clubStatsRaw = that.data.rankPage === 1 ? result : that.data.clubStatsRaw.concat(result);
                that.setData({ clubStatsRaw, rankFinished: list.length < limit });
                that.sortClubs();
              }
            }
          });
        });
      }
    });
  },
  sortClubs() {
    const mode = this.data.rankMode;
    const key = mode === 'members' ? 'member_count' : 'total_matches';
    const arr = (this.data.clubStatsRaw || []).slice();
    arr.sort((a, b) => (b[key] || 0) - (a[key] || 0));
    const limit = this.data.rankPage * 20;
    this.setData({ topClubs: arr.slice(0, limit) });
  },
  switchTab(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ currentTab: idx });
  },
  onUserInput(e) { this.setData({ userQuery: e.detail.value }); },
  onClubInput(e) { this.setData({ clubQuery: e.detail.value }); },
  hideKeyboard,
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
  switchUserDays(e) {
    const d = Number(e.currentTarget.dataset.days);
    this.setData({ userDays: d });
    this.fetchUserTrend();
  },
  switchMatchDays(e) {
    const d = Number(e.currentTarget.dataset.days);
    this.setData({ matchDays: d });
    this.fetchMatchActivity();
  },
  switchRankMode(e) {
    const mode = e.currentTarget.dataset.mode;
    if (mode === this.data.rankMode) return;
    this.setData({ rankMode: mode });
    this.sortClubs();
  },
  fetchUserTrend() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/sys/user_trend?days=${this.data.userDays}`,
      success(res) {
        const data = res.data || [];
        that.setData({ userTrend: data });
        that.drawLine('userTrend', data);
      }
    });
  },
  fetchMatchActivity() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/sys/match_activity?days=${this.data.matchDays}`,
      success(res) {
        const data = res.data || [];
        that.setData({ matchTrend: data });
        that.drawBars('matchActivity', data);
      }
    });
  },
  drawLine(id, data) {
    const ctx = wx.createCanvasContext(id, this);
    const width = 300;
    const height = 160;
    const max = Math.max.apply(null, data.map(d => d.count)) || 1;
    const step = data.length > 1 ? width / (data.length - 1) : width;
    ctx.clearRect(0, 0, width, height);
    ctx.beginPath();
    ctx.setStrokeStyle('#07C160');
    data.forEach((p, i) => {
      const x = i * step;
      const y = height - (p.count / max) * (height - 20);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.draw();
  },
  drawBars(id, data) {
    const ctx = wx.createCanvasContext(id, this);
    const width = 300;
    const height = 160;
    const max = Math.max.apply(null, data.map(d => d.count)) || 1;
    const step = width / data.length;
    const bar = step * 0.6;
    ctx.clearRect(0, 0, width, height);
    ctx.setFillStyle('#07C160');
    data.forEach((p, i) => {
      const x = i * step + (step - bar) / 2;
      const h = (p.count / max) * (height - 20);
      ctx.fillRect(x, height - h, bar, h);
    });
    ctx.draw();
  },
  openAllUsers() {
    wx.navigateTo({ url: '/pages/sys-user-list/index' });
  },
  openAllClubs() {
    wx.navigateTo({ url: '/pages/sys-club-list/index' });
  },
  openPending() {
    wx.navigateTo({ url: '/pages/sys-pending/index' });
  },
  openAllMatches() {
    wx.navigateTo({ url: '/pages/sys-match-list/index' });
  },
  openClub(e) {
    const cid = e.currentTarget.dataset.id;
    if (!cid) return;
    wx.navigateTo({ url: `/pages/manage/manage?cid=${cid}` });
  },
  onReachBottom() {
    if (this.data.currentTab !== 1 || this.data.rankFinished) return;
    this.setData({ rankPage: this.data.rankPage + 1 });
    this.loadClubStats();
  }
});
