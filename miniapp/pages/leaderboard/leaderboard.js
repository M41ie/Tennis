const BASE_URL = getApp().globalData.BASE_URL;

Page({
    data: {
      clubOptions: ['All'],
      clubIndex: 0,
      players: [],
      minRating: null,
      maxRating: null,
      ratingOptions: ['Singles', 'Doubles'],
      ratingIndex: 0,
      minAge: null,
      maxAge: null,
      gender: '',
    },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    const uid = wx.getStorageSync('user_id');
    if (!uid) {
      that.setData({ clubOptions: ['All'], clubIndex: 0 });
      that.fetchPlayers();
      return;
    }
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const list = res.data.joined_clubs || [];
        const options = ['All'].concat(list);
        const stored = wx.getStorageSync('club_id');
        let idx = 0;
        if (stored) {
          const i = list.indexOf(stored);
          if (i >= 0) idx = i + 1;
        }
        that.setData({ clubOptions: options, clubIndex: idx });
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
  onMinAge(e) { this.setData({ minAge: e.detail.value }); },
  onMaxAge(e) { this.setData({ maxAge: e.detail.value }); },
  onGender(e) { this.setData({ gender: e.detail.value }); },
  fetchPlayers() {
    const club = this.data.clubOptions[this.data.clubIndex];
    const that = this;
    let url;
    if (club !== 'All') {
      url = `${BASE_URL}/clubs/` + club + '/players';
    } else {
      url = `${BASE_URL}/players`;
    }
    const params = [];
    if (this.data.minRating) params.push('min_rating=' + this.data.minRating);
    if (this.data.maxRating) params.push('max_rating=' + this.data.maxRating);
    if (this.data.minAge) params.push('min_age=' + this.data.minAge);
    if (this.data.maxAge) params.push('max_age=' + this.data.maxAge);
    if (this.data.gender) params.push('gender=' + this.data.gender);
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
    const id = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.cid;
    wx.navigateTo({ url: '/pages/profile/profile?id=' + id + '&cid=' + cid });
  }
});
