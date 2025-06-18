const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const store = require('../../store/store');

Page({
  data: {
    t: zh_CN,
    clubIds: [],
    clubOptions: [],
    clubIndex: 0,
    players: [],
    playerNames: [],
    partnerNames: [],
    opponentIndex: 0,
    modeOptions: [zh_CN.chooseMatchType, zh_CN.singles, zh_CN.doubles],
    modeIndex: 0,
    partnerIndex: 0,
    opp1Index: 0,
    opp2Index: 0,
    date: '',
    today: '',
    location: '',
    // Display names for match formats
    formatOptions: [zh_CN.chooseFormat, '六局', '四局', '抢十', '抢七'],
    // Codes sent to the backend when submitting a result
    formatCodes: ['', '6_game', '4_game', 'tb10', 'tb7'],
    formatIndex: 0,
    scoreA: '',
    scoreB: ''
  },
  onLoad() {
    const today = new Date().toISOString().slice(0, 10);
    this.setData({ today });
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        const allClubs = res.data || [];
        const uid = store.userId;
        if (!uid) {
          const ids = [''];
          const names = [that.data.t.chooseClub];
          that.setData({ clubIds: ids, clubOptions: names, clubIndex: 0 });
          return;
        }
        request({
          url: `${BASE_URL}/users/${uid}`,
          success(uRes) {
            const joined = uRes.data.joined_clubs || [];
            const filtered = allClubs.filter(c => joined.includes(c.club_id));
            const ids = [''];
            const names = [that.data.t.chooseClub];
            ids.push(...filtered.map(c => c.club_id));
            names.push(...filtered.map(c => c.name));
            that.setData({ clubIds: ids, clubOptions: names, clubIndex: 0 });
          },
          fail() {
            const ids = [''];
            const names = [that.data.t.chooseClub];
            that.setData({ clubIds: ids, clubOptions: names, clubIndex: 0 });
          }
        });
      }
    });
  },
  fetchPlayers(cid) {
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/players`,
      success(res) {
        const uid = store.userId;
        const filtered = res.data.filter(p => p.user_id !== uid);
        const names = filtered.map(p => p.name);
        const players = [null, ...filtered];
        const playerNames = [that.data.t.chooseOpponent, ...names];
        const partnerNames = [that.data.t.choosePartner, ...names];
        that.setData({
          players,
          playerNames,
          partnerNames,
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
    if (cid) {
      this.fetchPlayers(cid);
    } else {
      this.setData({
        players: [],
        playerNames: [],
        partnerNames: [],
        opponentIndex: 0,
        partnerIndex: 0,
        opp1Index: 0,
        opp2Index: 0,
      });
    }
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
  hideKeyboard,
  submit() {
    const that = this;
    const doubles = this.data.modeIndex === 2;
    const incomplete =
      this.data.clubIndex === 0 ||
      this.data.modeIndex === 0 ||
      !this.data.date ||
      this.data.formatIndex === 0 ||
      this.data.scoreA === '' ||
      this.data.scoreB === '' ||
      (doubles
        ? this.data.partnerIndex === 0 ||
          this.data.opp1Index === 0 ||
          this.data.opp2Index === 0
        : this.data.opponentIndex === 0);
    if (incomplete) {
      wx.showToast({ title: this.data.t.incompleteInfo, icon: 'none' });
      return;
    }

    const cid = this.data.clubIds[this.data.clubIndex];
    const userId = store.userId;
    const token = store.token;
    if (!cid || !userId || !token) return;

    if (doubles) {
      const players = this.data.players;
      const partner = players[this.data.partnerIndex];
      const b1 = players[this.data.opp1Index];
      const b2 = players[this.data.opp2Index];
      request({
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
          wx.showToast({ title: that.data.t.submitSuccess, icon: 'success', duration: 1000 });
          setTimeout(() => {
            wx.navigateBack();
          }, 1000);
        }
      });
    } else {
      const opponent = this.data.players[this.data.opponentIndex];
      request({
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
          wx.showToast({ title: that.data.t.submitSuccess, icon: 'success', duration: 1000 });
          setTimeout(() => {
            wx.navigateBack();
          }, 1000);
        }
      });
    }
  }
});
