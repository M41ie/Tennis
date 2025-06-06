const BASE_URL = getApp().globalData.BASE_URL;
const { zh_CN } = require('../../utils/locales.js');

Page({
  data: {
    t: zh_CN,
    clubIds: [],
    clubOptions: [],
    clubIndex: 0,
    players: [],
    playerNames: [],
    opponentIndex: 0,
    modeOptions: ['Singles', 'Doubles'],
    modeIndex: 0,
    partnerIndex: 0,
    opp1Index: 0,
    opp2Index: 0,
    date: '',
    location: '',
    // Display names for match formats
    formatOptions: ['6局', '4局', '抢11', '抢10', '抢7'],
    // Codes sent to the backend when submitting a result
    formatCodes: ['6_game', '4_game', 'tb11', 'tb10', 'tb7'],
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
      url: `${BASE_URL}/clubs`,
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
      url: `${BASE_URL}/clubs/${cid}/players`,
      success(res) {
        const uid = wx.getStorageSync('user_id');
        const filtered = res.data.filter(p => p.user_id !== uid);
        const names = filtered.map(p => p.name);
        that.setData({
          players: filtered,
          playerNames: names,
          opponentIndex: 0,
          partnerIndex: 0,
          opp1Index: 0,
          opp2Index: 0,
        });
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
  onModeChange(e) {
    // picker values are strings; convert to number for strict comparisons
    this.setData({ modeIndex: Number(e.detail.value) });
  },
  onPartnerChange(e) { this.setData({ partnerIndex: e.detail.value }); },
  onOpp1Change(e) { this.setData({ opp1Index: e.detail.value }); },
  onOpp2Change(e) { this.setData({ opp2Index: e.detail.value }); },
  onDateChange(e) {
    this.setData({ date: e.detail.value });
  },
  onLocation(e) { this.setData({ location: e.detail.value }); },
  onFormatChange(e) { this.setData({ formatIndex: e.detail.value }); },
  onScoreA(e) { this.setData({ scoreA: e.detail.value }); },
  onScoreB(e) { this.setData({ scoreB: e.detail.value }); },
  submit() {
    const cid = this.data.clubIds[this.data.clubIndex];
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    if (!cid || !userId || !token) return;
    const doubles = this.data.modeIndex === 1;
    if (doubles) {
      const players = this.data.players;
      const partner = players[this.data.partnerIndex];
      const b1 = players[this.data.opp1Index];
      const b2 = players[this.data.opp2Index];
      if (!partner || !b1 || !b2) return;
      wx.request({
        url: `${BASE_URL}/clubs/${cid}/pending_doubles`,
        method: 'POST',
        data: {
          initiator: userId,
          partner: partner.user_id,
          opponent1: b1.user_id,
          opponent2: b2.user_id,
          score_initiator: parseInt(this.data.scoreA, 10),
          score_opponent: parseInt(this.data.scoreB, 10),
          date: this.data.date,
          format: this.data.formatCodes[this.data.formatIndex],
          location: this.data.location,
          token
        },
        success() {
          wx.showToast({ title: '已提交', icon: 'success' });
        }
      });
    } else {
      const opponent = this.data.players[this.data.opponentIndex];
      if (!opponent) return;
      wx.request({
        url: `${BASE_URL}/clubs/${cid}/pending_matches`,
        method: 'POST',
        data: {
          initiator: userId,
          opponent: opponent.user_id,
          score_initiator: parseInt(this.data.scoreA, 10),
          score_opponent: parseInt(this.data.scoreB, 10),
          date: this.data.date,
          format: this.data.formatCodes[this.data.formatIndex],
          location: this.data.location,
          token
        },
        success() {
          wx.showToast({ title: '已提交', icon: 'success' });
        }
      });
    }
  }
});
