const clubService = require('../../services/club');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const store = require('../../store/store');
const { t } = require('../../utils/locales');

Page({
  data: {
    t,
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
    clubService.getAppointments(cid).then(res => {
      that.setData({ appointments: res });
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
    clubService
      .createAppointment(cid, {
        user_id: userId,
        date: this.data.date,
        location: this.data.location,
        token,
      })
      .then(() => {
        that.fetch();
      });
  },
  signup(e) {
    const idx = e.currentTarget.dataset.idx;
    const cid = store.clubId;
    const userId = store.userId;
    const token = store.token;
    const that = this;
    clubService
      .signupAppointment(cid, idx, { user_id: userId, token })
      .then(() => {
        that.fetch();
      });
  },
  cancel(e) {
    const idx = e.currentTarget.dataset.idx;
    const cid = store.clubId;
    const userId = store.userId;
    const token = store.token;
    const that = this;
    clubService
      .cancelAppointment(cid, idx, { user_id: userId, token })
      .then(() => {
        that.fetch();
      });
  }
});
