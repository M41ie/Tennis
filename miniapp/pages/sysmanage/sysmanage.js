Page({
  data: {
    currentTab: 0,
    userQuery: '',
    clubQuery: ''
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
  }
});
