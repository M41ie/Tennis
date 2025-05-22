Page({
  data: {
    clubOptions: ['All'],
    clubIndex: 0,
    players: [],
    minRating: null,
    maxRating: null,
    ratingOptions: ['Singles', 'Doubles'],
    ratingIndex: 0,
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
  onRatingChange(e) {
    this.setData({ ratingIndex: e.detail.value });
    this.fetchPlayers();
  },
  onMinRating(e) { this.setData({ minRating: e.detail.value }); },
  onMaxRating(e) { this.setData({ maxRating: e.detail.value }); },
  fetchPlayers() {
    const club = this.data.clubOptions[this.data.clubIndex];
    const that = this;
    let url;
    if (club !== 'All') {
      url = 'http://localhost:8000/clubs/' + club + '/players';
    } else {
      url = 'http://localhost:8000/players';
    }
    const params = [];
    if (this.data.minRating) params.push('min_rating=' + this.data.minRating);
    if (this.data.maxRating) params.push('max_rating=' + this.data.maxRating);
    if (this.data.ratingIndex === 1) params.push('doubles=true');
    if (params.length) url += '?' + params.join('&');
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
