const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const store = require('../../store/store');

Page({
  data: {
    appointments: [],
    date: '',
    location: ''
  },
  onLoad() {
    this.fetch();
  },
  fetch() {
    const cid = store.clubId;
    const that = this;
    if (!cid) return;
    request({
      url: `${BASE_URL}/clubs/${cid}/appointments`,
      success(res) {
        that.setData({ appointments: res.data });
      }
    });
  },
  onDate(e) { this.setData({ date: e.detail.value }); },
  onLocation(e) { this.setData({ location: e.detail.value }); },
  hideKeyboard,
  create() {
    const cid = store.clubId;
    const userId = store.userId;
    const token = store.token;
    const that = this;
    if (!cid || !userId || !token) return;
    request({
      url: `${BASE_URL}/clubs/${cid}/appointments`,
      method: 'POST',
      data: { user_id: userId, date: this.data.date, location: this.data.location, token },
      success() { that.fetch(); }
    });
  },
  signup(e) {
    const idx = e.currentTarget.dataset.idx;
    const cid = store.clubId;
    const userId = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/appointments/${idx}/signup`,
      method: 'POST',
      data: { user_id: userId, token },
      success() { that.fetch(); }
    });
  },
  cancel(e) {
    const idx = e.currentTarget.dataset.idx;
    const cid = store.clubId;
    const userId = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/appointments/${idx}/cancel`,
      method: 'POST',
      data: { user_id: userId, token },
      success() { that.fetch(); }
    });
  }
});
