Page({
  data: {
    clubOptions: ['All'],
    clubIndex: 0,
    players: [],
    minRating: null,
    maxRating: null,
  },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: 'http://localhost:8000/clubs',
      success(res) {
        const options = ['All'].concat(res.data.map(c => c.club_id));
        that.setData({ clubOptions: options });
        that.fetchPlayers();
      }
    });
  },
  onClubChange(e) {
    this.setData({ clubIndex: e.detail.value });
    this.fetchPlayers();
  },
  onMinRating(e) { this.setData({ minRating: e.detail.value }); },
  onMaxRating(e) { this.setData({ maxRating: e.detail.value }); },
  fetchPlayers() {
    const club = this.data.clubOptions[this.data.clubIndex];
    const that = this;
    let url = 'http://localhost:8000/clubs';
    if (club !== 'All') url += '/' + club + '/players';
    else {
      // currently API lacks cross-club listing; use first club if available
      if (this.data.clubOptions.length > 1) {
        url += '/' + this.data.clubOptions[1] + '/players';
      }
    }
    wx.request({
      url,
      success(res) {
        that.setData({ players: res.data });
      }
    });
  },
  viewPlayer(e) {
    wx.navigateTo({ url: '/pages/profile/profile?id=' + e.currentTarget.dataset.id });
  }
});
