const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const store = require('../../store/store');

Page({
  data: {
    t: zh_CN,
    query: '',
    myClubs: [],
    allowCreate: false
  },
  onLoad() {
    this.getMyClubs();
    this.checkPermission();
  },
  onInput(e) {
    this.setData({ query: e.detail.value });
  },
  onSearch() {
    const q = this.data.query.trim();
    const url = q ? `/pages/joinclub/joinclub?query=${q}` : '/pages/joinclub/joinclub';
    wx.navigateTo({ url });
  },
  hideKeyboard,
  joinClub(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = store.userId;
    const token = store.token;
    const that = this;
    if (!uid || !token) return;
    request({
      url: `${BASE_URL}/clubs/${cid}/join`,
      method: 'POST',
      data: { user_id: uid, token },
      complete() {
        that.searchClubs();
        that.getMyClubs();
      }
    });
  },
  getMyClubs() {
    const uid = store.userId;
    if (!uid) return;
    const that = this;
    request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const ids = res.data.joined_clubs || [];
        if (!ids.length) {
          that.setData({ myClubs: [] });
          return;
        }
        const list = [];
        let count = 0;
        ids.forEach(cid => {
          request({
            url: `${BASE_URL}/clubs/${cid}`,
            success(r) {
              const info = r.data;
              const stats = info.stats || {};
              const sr = stats.singles_rating_range || [];
              const dr = stats.doubles_rating_range || [];
              const fmt = n => (typeof n === 'number' ? n.toFixed(1) : '--');
              const singlesAvg =
                typeof stats.singles_avg_rating === 'number'
                  ? fmt(stats.singles_avg_rating)
                  : '--';
              const doublesAvg =
                typeof stats.doubles_avg_rating === 'number'
                  ? fmt(stats.doubles_avg_rating)
                  : '--';
              let role = 'member';
              if (info.leader_id === uid) role = 'leader';
              else if (info.admin_ids && info.admin_ids.includes(uid)) role = 'admin';
              list.push({
                club_id: cid,
                name: info.name,
                slogan: info.slogan || '',
                region: info.region || '',
                role,
                roleText: role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员',
                member_count: stats.member_count,
                singles_range: sr.length ? `${fmt(sr[0])}-${fmt(sr[1])}` : '--',
                doubles_range: dr.length ? `${fmt(dr[0])}-${fmt(dr[1])}` : '--',
                total_singles: stats.total_singles_matches != null ?
                  stats.total_singles_matches.toFixed(0) : '--',
                total_doubles: stats.total_doubles_matches != null ?
                  stats.total_doubles_matches.toFixed(0) : '--',
                singles_avg: singlesAvg,
                doubles_avg: doublesAvg
              });
            },
            complete() {
              count++;
              if (count === ids.length) {
                that.setData({ myClubs: list });
              }
            }
          });
        });
      }
    });
  },
  openClub(e) {
    const cid = e.currentTarget.dataset.id;
    if (cid) {
      store.setClubId(cid);
      wx.navigateTo({ url: `/pages/manage/manage?cid=${cid}` });
    }
  },
  quitClub(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'quit' },
      complete() { that.getMyClubs(); }
    });
  },
  resignAdmin(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = store.userId;
    const token = store.token;
    const that = this;
    wx.showModal({
      title: '确认卸任',
      content: '确认要卸任该俱乐部的管理员吗？',
      confirmColor: '#e03a3a',
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
            data: { user_id: uid, token, action: 'resign_admin' },
            complete() { that.getMyClubs(); }
          });
        }
      }
    });
  },
  toggleAdmin(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'toggle_admin' },
      complete() { that.getMyClubs(); }
    });
  },
  transferLeader(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'transfer_leader' },
      complete() { that.getMyClubs(); }
    });
  },
  checkPermission() {
    const uid = store.userId;
    if (!uid) return;
    const that = this;
    request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const created = res.data.created_clubs != null ? res.data.created_clubs : 0;
        const max = res.data.max_creatable_clubs != null ? res.data.max_creatable_clubs : 0;
        that.setData({ allowCreate: created < max });
      }
    });
  },
  createClub() {
    if (this.data.allowCreate) {
      wx.navigateTo({ url: '/pages/createclub/createclub' });
    } else {
      wx.showToast({ title: '创建俱乐部的数量已达上限', icon: 'none' });
    }
  }
});
