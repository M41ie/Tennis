const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [],
    players: [],
    filter: {
      clubs: [],
      mode: 'Singles',
      minLevel: '',
      maxLevel: '',
      gender: 'All',
      minAge: '',
      maxAge: ''
    },
    showClubDialog: false,
    showLevelDialog: false,
    showAgeDialog: false,
    selectedClubs: [],
    levelMin: '',
    levelMax: '',
    ageMin: '',
    ageMax: ''
  },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        const list = res.data.map(c => c.club_id || c.name);
        that.setData({
          clubs: list,
          selectedClubs: list.slice(),
          filter: { ...that.data.filter, clubs: list.slice() }
        });
        that.fetchList(that.data.filter);
      }
    });
  },
  openClub() { this.setData({ showClubDialog: true }); },
  onClubsChange(e) { this.setData({ selectedClubs: e.detail.value }); },
  confirmClub() {
    const filter = { ...this.data.filter, clubs: this.data.selectedClubs };
    this.setData({ filter, showClubDialog: false });
    this.fetchList(filter);
  },
  chooseMode() {
    const that = this;
    wx.showActionSheet({
      itemList: ['Singles', 'Doubles'],
      success(res) {
        if (res.tapIndex >= 0) {
          const mode = res.tapIndex === 1 ? 'Doubles' : 'Singles';
          const filter = { ...that.data.filter, mode };
          that.setData({ filter });
          that.fetchList(filter);
        }
      }
    });
  },
  openLevel() {
    this.setData({
      showLevelDialog: true,
      levelMin: this.data.filter.minLevel,
      levelMax: this.data.filter.maxLevel
    });
  },
  onLevelMin(e) { this.setData({ levelMin: e.detail.value }); },
  onLevelMax(e) { this.setData({ levelMax: e.detail.value }); },
  confirmLevel() {
    const filter = { ...this.data.filter, minLevel: this.data.levelMin, maxLevel: this.data.levelMax };
    this.setData({ filter, showLevelDialog: false });
    this.fetchList(filter);
  },
  chooseGender() {
    const that = this;
    wx.showActionSheet({
      itemList: ['All', 'Male', 'Female'],
      success(res) {
        if (res.tapIndex >= 0) {
          const gender = ['All', 'Male', 'Female'][res.tapIndex];
          const filter = { ...that.data.filter, gender };
          that.setData({ filter });
          that.fetchList(filter);
        }
      }
    });
  },
  openAge() {
    this.setData({
      showAgeDialog: true,
      ageMin: this.data.filter.minAge,
      ageMax: this.data.filter.maxAge
    });
  },
  onAgeMin(e) { this.setData({ ageMin: e.detail.value }); },
  onAgeMax(e) { this.setData({ ageMax: e.detail.value }); },
  confirmAge() {
    const filter = { ...this.data.filter, minAge: this.data.ageMin, maxAge: this.data.ageMax };
    this.setData({ filter, showAgeDialog: false });
    this.fetchList(filter);
  },
  fetchList(filter) {
    const clubs = filter.clubs && filter.clubs.length ? filter.clubs : ['All'];
    const club = clubs[0];
    const that = this;
    let url;
    if (club !== 'All') {
      url = `${BASE_URL}/clubs/` + club + '/players';
    } else {
      url = `${BASE_URL}/players`;
    }
    const params = [];
    if (filter.minLevel) params.push('min_rating=' + filter.minLevel);
    if (filter.maxLevel) params.push('max_rating=' + filter.maxLevel);
    if (filter.minAge) params.push('min_age=' + filter.minAge);
    if (filter.maxAge) params.push('max_age=' + filter.maxAge);
    if (filter.gender && filter.gender !== 'All') params.push('gender=' + filter.gender);
    if (filter.mode === 'Doubles') params.push('doubles=true');
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
