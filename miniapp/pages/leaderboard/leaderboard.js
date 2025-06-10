const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [], // [{id, name, checked}]
    players: [],
    filter: {
      clubs: [],
      mode: 'Singles',
      gender: 'All'
    },
    showClubDialog: false,
    genderText: '男子&女子'
  },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        const clubList = (res.data || []).map(c => ({
          id: c.club_id || c.name,
          name: c.name || c.club_id,
          checked: true
        }));
        const ids = clubList.map(c => c.id);
        that.setData({
          clubs: clubList,
          filter: { ...that.data.filter, clubs: ids }
        });
        that.fetchJoined(ids);
      }
    });
  },
  fetchJoined(list) {
    const uid = wx.getStorageSync('user_id');
    const that = this;
    if (!uid) {
      // User not logged in. Clear selected clubs so no ranking
      // list is shown by default.
      const newClubs = that.data.clubs.map(c => ({ ...c, checked: false }));
      that.setData({
        clubs: newClubs,
        filter: { ...that.data.filter, clubs: [] },
        players: []
      });
      return;
    }
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const joined = res.data.joined_clubs || [];
        const sel = list.filter(c => joined.includes(c));
        const selected = sel.length ? sel : list.slice();
        const newClubs = that.data.clubs.map(club => ({
          ...club,
          checked: selected.includes(club.id)
        }));
        that.setData({
          clubs: newClubs,
          filter: { ...that.data.filter, clubs: selected }
        });
        that.fetchList(that.data.filter);
      },
      fail() {
        that.setData({
          clubs: that.data.clubs.map(c => ({ ...c, checked: true })),
          filter: { ...that.data.filter, clubs: list.slice() }
        });
        that.fetchList(that.data.filter);
      }
    });
  },
  openClub() { this.setData({ showClubDialog: true }); },
  onClubsChange(e) {
    const ids = e.detail.value;
    const clubs = this.data.clubs.map(c => ({ ...c, checked: ids.includes(c.id) }));
    this.setData({ clubs });
  },
  confirmClub() {
    // Extract currently selected clubs from the object list
    const selectedClubs = this.data.clubs.filter(club => club.checked);
    const selectedClubIds = selectedClubs.map(club => club.id);

    const filter = { ...this.data.filter, clubs: selectedClubIds };
    this.setData({ filter, showClubDialog: false });
    // Re-fetch ranking list using the updated club filter
    this.fetchList(filter);
  },
  selectAllClubs() {
    const clubs = this.data.clubs.map(c => ({ ...c, checked: true }));
    this.setData({ clubs });
  },
  clearClubs() {
    const clubs = this.data.clubs.map(c => ({ ...c, checked: false }));
    this.setData({ clubs });
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
      itemList: ['男子&女子', '男子', '女子'],
      success(res) {
        if (res.tapIndex >= 0) {
          const genders = ['All', 'Male', 'Female'];
          const texts = ['男子&女子', '男子', '女子'];
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
          if (p.weighted_singles_matches != null) p.weighted_singles_matches = p.weighted_singles_matches.toFixed(2);
          if (p.weighted_doubles_matches != null) p.weighted_doubles_matches = p.weighted_doubles_matches.toFixed(2);
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
