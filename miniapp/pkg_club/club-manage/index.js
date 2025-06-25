const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const { formatClubCardData } = require('../../utils/clubFormat');
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
    const url = q ? `/pkg_club/joinclub/joinclub?query=${q}` : '/pkg_club/joinclub/joinclub';
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
        const idsParam = ids.join(',');
        request({
          url: `${BASE_URL}/clubs/batch?club_ids=${idsParam}`,
          success(r) {
            const infos = r.data || [];
            const list = infos.map(info => formatClubCardData(info, uid));
            that.setData({ myClubs: list });
          }
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
      title: this.data.t.confirmResign,
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
      wx.navigateTo({ url: '/pkg_club/createclub/createclub' });
    } else {
      wx.showToast({ duration: 4000,  title: '创建俱乐部的数量已达上限', icon: 'none' });
    }
  }
});
