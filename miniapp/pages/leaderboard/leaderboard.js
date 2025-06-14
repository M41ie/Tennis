const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [], // picker options {id, name}
    allClubIds: [],
    joinedClubIds: [],
    selectedClub: '_global',
    selectedClubIndex: 0,
    selectedClubText: '全局排行',
    players: [],
    filter: {
      clubs: [],
      mode: 'Singles',
      gender: 'All',
      region: ''
    },
    genderOptions: ['男子&女子', '男子', '女子'],
    genderIndex: 0,
    genderText: '男子&女子',
    region: ['-', '-', '-'],
    regionText: '全国',
    page: 1,
    finished: false
  },
  onLoad() {
    this.fetchInitial();
  },
  fetchInitial() {
    const uid = wx.getStorageSync('user_id');
    const that = this;
    const params = [];
    params.push('include_clubs=true');
    if (uid) {
      params.push('user_id=' + uid);
      params.push('include_joined=true');
    }
    const url = `${BASE_URL}/leaderboard_full?` + params.join('&');
    wx.request({
      url,
      success(res) {
        const data = res.data || {};
        const list = data.clubs || [];
        const ids = list.map(c => c.club_id || c.name);
        const map = {};
        list.forEach(c => { map[c.club_id || c.name] = c.name || c.club_id; });
        that.clubNameMap = map;
        const joined = data.joined_clubs || [];
        const options = that.buildClubOptions(joined);
        const selected = joined.length ? '_my' : '_global';
        const clubIds = joined.length ? joined.slice() : ids;
        const index = options.findIndex(o => o.id === selected);
        data.players = data.players || [];
        data.players.forEach(p => {
          const key = that.data.filter.mode === 'Doubles' ? 'doubles_rating' : 'singles_rating';
          const rating = p[key];
          p.rating = rating != null ? Number(rating).toFixed(3) : '--';
          if (p.weighted_singles_matches != null) p.weighted_singles_matches = p.weighted_singles_matches.toFixed(2);
          if (p.weighted_doubles_matches != null) p.weighted_doubles_matches = p.weighted_doubles_matches.toFixed(2);
        });
        const filter = { ...that.data.filter, clubs: clubIds };
        that.setData({
          allClubIds: ids,
          joinedClubIds: joined,
          selectedClub: selected,
          selectedClubIndex: index,
          selectedClubText: options[index].name,
          filter,
          players: [],
          page: 1,
          finished: false
        }, () => {
          that.fetchList(filter);
        });
      },
      fail() {
        that.setData({ allClubIds: [], joinedClubIds: [] });
      }
    });
  },
  buildClubOptions(joined) {
    const options = [
      { id: '_global', name: '全局排行' },
      { id: '_my', name: '所属俱乐部' }
    ];
    joined.forEach(cid => {
      const name = this.clubNameMap[cid] || cid;
      options.push({ id: cid, name });
    });
    this.setData({ clubs: options });
    return options;
  },
  onClubSelect(e) {
    const index = Number(e.detail.value);
    const item = this.data.clubs[index];
    if (!item) return;
    const selected = item.id;
    let clubs = [];
    if (selected === '_global') clubs = this.data.allClubIds;
    else if (selected === '_my') clubs = this.data.joinedClubIds;
    else clubs = [selected];
    const filter = { ...this.data.filter, clubs };
    this.setData({
      selectedClub: selected,
      selectedClubIndex: index,
      selectedClubText: item.name,
      filter,
      page: 1,
      players: [],
      finished: false
    });
    this.fetchList(filter);
  },
  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    if (mode === this.data.filter.mode) return;
    const filter = { ...this.data.filter, mode };
    this.setData({ filter, page: 1, players: [], finished: false });
    this.fetchList(filter);
  },
  onGender(e) {
    const index = Number(e.detail.value);
    const genders = ['All', 'Male', 'Female'];
    const gender = genders[index] || 'All';
    const genderText = this.data.genderOptions[index] || '男子&女子';
    const filter = { ...this.data.filter, gender };
    this.setData({ genderIndex: index, genderText, filter, page: 1, players: [], finished: false });
    this.fetchList(filter);
  },
  onRegionChange(e) {
    const region = e.detail.value;
    const parts = region.filter(r => r && r !== '-');
    const regionString = parts.join(' ');
    const regionText = parts.length ? parts.join('-') : '全国';
    const filter = { ...this.data.filter, region: regionString };
    this.setData({ region, regionText, filter, page: 1, players: [], finished: false });
    this.fetchList(filter);
  },
  fetchList(filter) {
    const clubs = filter.clubs && filter.clubs.length ? filter.clubs : [];
    const that = this;
    const params = [];
    const limit = 50;
    const offset = (this.data.page - 1) * limit;
    if (filter.gender && filter.gender !== 'All') params.push('gender=' + filter.gender);
    if (filter.mode === 'Doubles') params.push('doubles=true');
    if (filter.region) params.push('region=' + encodeURIComponent(filter.region));
    params.push('include_clubs=false');
    params.push('include_joined=false');
    params.push('limit=' + limit);
    if (offset) params.push('offset=' + offset);
    if (clubs.length) params.push('club=' + clubs.join(','));
    const url = `${BASE_URL}/leaderboard_full` + (params.length ? '?' + params.join('&') : '');

    wx.request({
      url,
      success(res) {
        const list = (res.data && res.data.players) || [];
        list.forEach(p => {
          const key = that.data.filter.mode === 'Doubles' ? 'doubles_rating' : 'singles_rating';
          const rating = p[key];
          p.rating = rating != null ? Number(rating).toFixed(3) : '--';
          if (p.weighted_singles_matches != null) p.weighted_singles_matches = p.weighted_singles_matches.toFixed(2);
          if (p.weighted_doubles_matches != null) p.weighted_doubles_matches = p.weighted_doubles_matches.toFixed(2);
        });
        const players = that.data.page === 1 ? list : that.data.players.concat(list);
        that.setData({ players, finished: list.length < limit });
      }
    });
  },
  viewPlayer(e) {
    const id = e.currentTarget.dataset.id;
    const cid = e.currentTarget.dataset.cid;
    wx.navigateTo({ url: '/pages/profile/profile?id=' + id + '&cid=' + cid });
  },
  onReachBottom() {
    if (this.data.finished) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchList(this.data.filter);
  }
});
