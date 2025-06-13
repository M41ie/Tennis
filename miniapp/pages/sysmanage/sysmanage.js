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
        that.setData({ topClubs: list.slice(0, 10) });
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
  }
});
