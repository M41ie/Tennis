const clubService = require('../../services/club');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { withBase } = require('../../utils/format');

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
      region: '',
      sort: 'rating'
    },
    genderOptions: ['男子&女子', '男子', '女子'],
    genderIndex: 0,
    genderText: '男子&女子',
    sortOptions: ['评分', '场次'],
    sortIndex: 0,
    sortText: '评分',
    region: ['-', '-', '-'],
    regionText: '全国',
    page: 1,
    finished: false,
    isLoading: true,
    isError: false,
    isEmpty: false
  },
  hideKeyboard,
  onLoad() {
    this.fetchInitial();
  },
  fetchInitial() {
    const uid = store.userId;
    const that = this;
    const params = { include_clubs: true };
    this.setData({ isLoading: true, isError: false, isEmpty: false });
    if (uid) {
      params.user_id = uid;
      params.include_joined = true;
    }
    clubService.getLeaderboard(params).then(data => {
        const list = data.clubs || [];
        const ids = list.map(c => c.club_id || c.name);
        const map = {};
        list.forEach(c => { map[c.club_id || c.name] = c.name || c.club_id; });
        that.clubNameMap = map;
        const joined = data.joined_clubs || [];
        const options = that.buildClubOptions(joined);
        const selected = joined.length ? '_my' : '_global';
        const clubIds = joined.length ? joined.slice() : [];
        const index = options.findIndex(o => o.id === selected);
        data.players = data.players || [];
        data.players.forEach(p => {
          const key = that.data.filter.mode === 'Doubles' ? 'doubles_rating' : 'singles_rating';
          const rating = p[key];
          p.rating = rating != null ? Number(rating).toFixed(3) : '--';
          if (p.weighted_singles_matches != null) p.weighted_singles_matches = p.weighted_singles_matches.toFixed(2);
          if (p.weighted_doubles_matches != null) p.weighted_doubles_matches = p.weighted_doubles_matches.toFixed(2);
          p.avatar = withBase(p.avatar || p.avatar_url);
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
    }).catch(() => {
      that.setData({ allClubIds: [], joinedClubIds: [], isLoading: false, isError: true });
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
    if (selected === '_global') clubs = [];
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
  onSortChange(e) {
    const index = Number(e.detail.value);
    const sort = index === 1 ? 'matches' : 'rating';
    const sortText = this.data.sortOptions[index] || '评分';
    const filter = { ...this.data.filter, sort };
    this.setData({ sortIndex: index, sortText, filter, page: 1, players: [], finished: false });
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
    this.setData({ isLoading: this.data.page === 1, isError: false });
    const params = { include_clubs: false, include_joined: false };
    const limit = 50;
    const offset = (this.data.page - 1) * limit;
    if (filter.gender && filter.gender !== 'All') params.gender = filter.gender;
    if (filter.mode === 'Doubles') params.doubles = true;
    if (filter.region) params.region = filter.region;
    if (filter.sort === 'matches') params.sort = 'matches';
    params.limit = limit;
    if (offset) params.offset = offset;
    if (clubs.length) params.club = clubs.join(',');

    clubService.getLeaderboard(params).then(res => {
        const list = (res.players) || [];
        list.forEach(p => {
          const key = that.data.filter.mode === 'Doubles' ? 'doubles_rating' : 'singles_rating';
          const rating = p[key];
          p.rating = rating != null ? Number(rating).toFixed(3) : '--';
          if (p.weighted_singles_matches != null) p.weighted_singles_matches = p.weighted_singles_matches.toFixed(2);
          if (p.weighted_doubles_matches != null) p.weighted_doubles_matches = p.weighted_doubles_matches.toFixed(2);
          p.avatar = withBase(p.avatar || p.avatar_url);
        });
        if (that.data.page === 1) {
          that.setData({
            players: list,
            finished: list.length < limit,
            isLoading: false,
            isEmpty: list.length === 0
          });
        } else {
          const start = that.data.players.length;
          const obj = { finished: list.length < limit, isLoading: false };
          list.forEach((item, i) => {
            obj[`players[${start + i}]`] = item;
          });
          that.setData(obj);
        }
    }).catch(() => {
        that.setData({ isLoading: false, isError: true });
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
