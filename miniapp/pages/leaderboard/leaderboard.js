const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [],
    players: [],
    filter: {
      clubs: [],
      mode: 'Singles',
      gender: 'All'
    },
    showClubDialog: false,
    genderText: '全性别',
    selectedClubs: []
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
  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    if (mode === this.data.filter.mode) return;
    const filter = { ...this.data.filter, mode };
    this.setData({ filter });
    this.fetchList(filter);
  },
  chooseGender() {
    const that = this;
    wx.showActionSheet({
      itemList: ['全性别', '男性', '女性'],
      success(res) {
        if (res.tapIndex >= 0) {
          const genders = ['All', 'Male', 'Female'];
          const texts = ['全性别', '男性', '女性'];
          const gender = genders[res.tapIndex];
          const genderText = texts[res.tapIndex];
          const filter = { ...that.data.filter, gender };
          that.setData({ filter, genderText });
          that.fetchList(filter);
        }
      }
    });
  },
  fetchList(filter) {
    const clubs = filter.clubs && filter.clubs.length ? filter.clubs : [];
    const that = this;
    const params = [];
    if (filter.gender && filter.gender !== 'All') params.push('gender=' + filter.gender);
    if (filter.mode === 'Doubles') params.push('doubles=true');

    let url = `${BASE_URL}/players`;
    if (clubs.length) params.push('club=' + clubs.join(','));
    if (params.length) url += '?' + params.join('&');

    wx.request({
      url,
      success(res) {
        const list = res.data || [];
        list.forEach(p => {
          if (p.rating != null) p.rating = p.rating.toFixed(3);
        });
        that.setData({ players: list });
      }
    });
  },
  viewPlayer(e) {
    const id = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.cid;
    wx.navigateTo({ url: '/pages/profile/profile?id=' + id + '&cid=' + cid });
  }
});
