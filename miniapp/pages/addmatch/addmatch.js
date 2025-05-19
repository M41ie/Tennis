Page({
  data: {
    clubIds: [],
    clubOptions: [],
    clubIndex: 0,
    players: [],
    playerNames: [],
    opponentIndex: 0,
    date: '',
    location: '',
    formatOptions: ['6_game', 'pro_set', '3_set', 'tb11', 'tb10', 'tb7'],
    formatIndex: 0,
    scoreA: '',
    scoreB: ''
  },
  onLoad() {
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: 'http://localhost:8000/clubs',
      success(res) {
        const ids = res.data.map(c => c.club_id);
        const names = res.data.map(c => c.name);
        that.setData({ clubIds: ids, clubOptions: names });
        const stored = wx.getStorageSync('club_id');
        const idx = ids.indexOf(stored);
        if (idx >= 0) {
          that.setData({ clubIndex: idx });
          that.fetchPlayers(ids[idx]);
        }
      }
    });
  },
  fetchPlayers(cid) {
    const that = this;
    wx.request({
      url: `http://localhost:8000/clubs/${cid}/players`,
      success(res) {
        const names = res.data.map(p => p.name);
        that.setData({ players: res.data, playerNames: names, opponentIndex: 0 });
      }
    });
  },
  onClubChange(e) {
    const idx = e.detail.value;
    this.setData({ clubIndex: idx });
    const cid = this.data.clubIds[idx];
    this.fetchPlayers(cid);
  },
  onOpponentChange(e) {
    this.setData({ opponentIndex: e.detail.value });
  },
  onDateChange(e) {
    this.setData({ date: e.detail.value });
  },
  onLocation(e) { this.setData({ location: e.detail.value }); },
  onFormatChange(e) { this.setData({ formatIndex: e.detail.value }); },
  onScoreA(e) { this.setData({ scoreA: e.detail.value }); },
  onScoreB(e) { this.setData({ scoreB: e.detail.value }); },
  submit() {
    const cid = this.data.clubIds[this.data.clubIndex];
    const opponent = this.data.players[this.data.opponentIndex];
    const userId = wx.getStorageSync('user_id');
    if (!cid || !opponent || !userId) return;
    wx.request({
      url: `http://localhost:8000/clubs/${cid}/pending_matches`,
      method: 'POST',
      data: {
        initiator: userId,
        opponent: opponent.user_id,
        score_initiator: parseInt(this.data.scoreA, 10),
        score_opponent: parseInt(this.data.scoreB, 10),
        date: this.data.date,
        format: this.data.formatOptions[this.data.formatIndex],
        location: this.data.location
      },
      success() {
        wx.showToast({ title: 'Submitted', icon: 'success' });
      }
    });
  }
});
