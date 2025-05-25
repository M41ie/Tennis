const BASE_URL = getApp().globalData.BASE_URL;

Page({
    data: {
      clubOptions: [],
      selectedClubs: [],
      showClubSel: false,
      players: [],
      minRating: '',
      maxRating: '',
      ratingOptions: ['Singles', 'Doubles'],
      ratingIndex: 0,
      genderOptions: ['All', 'M', 'F'],
      genderIndex: 0,
      minAge: '',
      maxAge: '',
    },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    const uid = wx.getStorageSync('user_id');
    if (!uid) {
      that.setData({ clubOptions: [], selectedClubs: [] });
      that.fetchPlayers();
      return;
    }
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const list = res.data.joined_clubs || [];
        that.setData({ clubOptions: list, selectedClubs: list.slice() });
        that.fetchPlayers();
      }
    });
  },
  toggleClubSel() {
    this.setData({ showClubSel: !this.data.showClubSel });
  },
  onClubsChange(e) {
    this.setData({ selectedClubs: e.detail.value });
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
  onGenderChange(e) {
    this.setData({ genderIndex: e.detail.value });
    this.fetchPlayers();
  },
  fetchPlayers() {
    const clubs = this.data.selectedClubs;
    const that = this;
    const params = [];
    if (this.data.minRating) params.push('min_rating=' + this.data.minRating);
    if (this.data.maxRating) params.push('max_rating=' + this.data.maxRating);
    if (this.data.minAge) params.push('min_age=' + this.data.minAge);
    if (this.data.maxAge) params.push('max_age=' + this.data.maxAge);
    const gender = this.data.genderOptions[this.data.genderIndex];
    if (gender !== 'All') params.push('gender=' + gender);
    if (this.data.ratingIndex === 1) params.push('doubles=true');
    const query = params.length ? '?' + params.join('&') : '';

    if (!clubs.length || clubs.length === this.data.clubOptions.length) {
      wx.request({
        url: `${BASE_URL}/players` + query,
        success(res) {
          that.setData({ players: res.data });
        }
      });
      return;
    }

    const promises = clubs.map((c) => {
      return new Promise((resolve) => {
        wx.request({
          url: `${BASE_URL}/clubs/` + c + '/players' + query,
          success(res) {
            const data = res.data.map((p) => {
              p.club_id = c;
              return p;
            });
            resolve(data);
          },
          fail() { resolve([]); }
        });
      });
    });
    Promise.all(promises).then((results) => {
      let all = [];
      results.forEach((r) => { all = all.concat(r); });
      all.sort((a, b) => b.rating - a.rating);
      that.setData({ players: all });
    });
  },
  viewPlayer(e) {
    const id = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.cid;
    wx.navigateTo({ url: '/pages/profile/profile?id=' + id + '&cid=' + cid });
  }
});
