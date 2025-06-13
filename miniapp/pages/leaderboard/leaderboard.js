const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [], // radio options {id, name}
    allClubIds: [],
    joinedClubIds: [],
    selectedClub: '_global',
    players: [],
    filter: {
      clubs: [],
      mode: 'Singles',
      gender: 'All',
      region: ''
    },
    showClubDialog: false,
    genderText: '男子&女子',
    region: [],
    regionText: '全国'
  },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        const list = res.data || [];
        const ids = list.map(c => c.club_id || c.name);
        const map = {};
        list.forEach(c => { map[c.club_id || c.name] = c.name || c.club_id; });
        that.clubNameMap = map;
        that.setData({ allClubIds: ids });
        that.fetchJoined();
      }
    });
  },
  fetchJoined() {
    const uid = wx.getStorageSync('user_id');
    const that = this;
    if (!uid) {
      that.buildClubOptions([]);
      const filter = { ...that.data.filter, clubs: that.data.allClubIds };
      that.setData({ selectedClub: '_global', joinedClubIds: [], filter });
      that.fetchList(filter);
      return;
    }
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const joined = res.data.joined_clubs || [];
        that.setData({ joinedClubIds: joined });
        that.buildClubOptions(joined);
        const selected = joined.length ? '_my' : '_global';
        const clubs = joined.length ? joined.slice() : that.data.allClubIds;
        that.setData({ selectedClub: selected, filter: { ...that.data.filter, clubs } });
        that.fetchList(that.data.filter);
      },
      fail() {
        that.buildClubOptions([]);
        const filter = { ...that.data.filter, clubs: that.data.allClubIds };
        that.setData({ selectedClub: '_global', joinedClubIds: [], filter });
        that.fetchList(filter);
      }
    });
  },
  buildClubOptions(joined) {
    const options = [
      { id: '_global', name: '全局排行' },
      { id: '_my', name: '我的所有俱乐部' }
    ];
    joined.forEach(cid => {
      const name = this.clubNameMap[cid] || cid;
      options.push({ id: cid, name });
    });
    this.setData({ clubs: options });
  },
  openClub() { this.setData({ showClubDialog: true }); },
  onClubsChange(e) {
    this.setData({ selectedClub: e.detail.value });
  },
  confirmClub() {
    let clubs = [];
    const selected = this.data.selectedClub;
    if (selected === '_global') clubs = this.data.allClubIds;
    else if (selected === '_my') clubs = this.data.joinedClubIds;
    else clubs = [selected];
    const filter = { ...this.data.filter, clubs };
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
  onRegionChange(e) {
    const region = e.detail.value;
    const regionString = region.join(' ');
    const regionText = regionString || '全国';
    const filter = { ...this.data.filter, region: regionString };
    this.setData({ region, regionText, filter });
    this.fetchList(filter);
  },
  fetchList(filter) {
    const clubs = filter.clubs && filter.clubs.length ? filter.clubs : [];
    const that = this;
    const params = [];
    if (filter.gender && filter.gender !== 'All') params.push('gender=' + filter.gender);
    if (filter.mode === 'Doubles') params.push('doubles=true');
    if (filter.region) params.push('region=' + encodeURIComponent(filter.region));

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
