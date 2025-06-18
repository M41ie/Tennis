const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { formatClubCardData } = require('../../utils/clubFormat');

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
    request({
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
    request({
      url: `${BASE_URL}/clubs/search?limit=${limit}&offset=${offset}`,
      success(res) {
        const list = res.data || [];
        if (!list.length) {
          if (that.data.rankPage === 1) {
            that.setData({ clubStatsRaw: [], topClubs: [] });
          }
          that.setData({ rankFinished: true });
          return;
        }
        const result = list.map(info => {
          return {
            ...formatClubCardData(info),
            total_matches: info.total_matches,
            pending_members: info.pending_members
          };
        });
        if (that.data.rankPage === 1) {
          that.setData({ clubStatsRaw: result, rankFinished: list.length < limit });
        } else {
          const start = that.data.clubStatsRaw.length;
          const obj = { rankFinished: list.length < limit };
          result.forEach((item, i) => {
            obj[`clubStatsRaw[${start + i}]`] = item;
          });
          that.setData(obj);
        }
        that.sortClubs();
      }
    });
  },
  sortClubs() {
    const mode = this.data.rankMode;
    const key = mode === 'members' ? 'member_count' : 'total_matches';
    const arr = (this.data.clubStatsRaw || []).slice();
    arr.sort((a, b) => (b[key] || 0) - (a[key] || 0));
    // Show all loaded clubs without slicing so the list isn't capped
    this.setData({ topClubs: arr });
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
    const url = q ? `/pkg_manage/sys-user-list/index?query=${q}` : '/pkg_manage/sys-user-list/index';
    wx.navigateTo({ url });
  },
  searchClubs() {
    const q = this.data.clubQuery.trim();
    const url = q ? `/pkg_manage/sys-club-list/index?query=${q}` : '/pkg_manage/sys-club-list/index';
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
    request({
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
    request({
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
    wx.navigateTo({ url: '/pkg_manage/sys-user-list/index' });
  },
  openAllClubs() {
    wx.navigateTo({ url: '/pkg_manage/sys-club-list/index' });
  },
  openPending() {
    wx.navigateTo({ url: '/pkg_manage/sys-pending/index' });
  },
  openAllMatches() {
    wx.navigateTo({ url: '/pkg_manage/sys-match-list/index' });
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
