const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const { formatJoinClubCardData } = require('../../utils/clubFormat');
const store = require('../../store/store');
const ensureSubscribe = require('../../utils/ensureSubscribe');

Page({
  data: {
    t: zh_CN,
    clubs: [],
    query: '',
    joined: [],
    showDialog: false,
    joinClubId: '',
    needRating: false,
    rating: '',
    reason: '',
    directClubId: ''
  },
  onLoad(options) {
    if (options && options.query) {
      this.setData({ query: options.query });
    }
    if (options && options.cid) {
      this.setData({ directClubId: options.cid });
    }
    this.fetchJoined();
  },
  fetchJoined() {
    const uid = store.userId;
    const that = this;
    if (!uid) {
      this.setData({ joined: [] });
      this.fetchClubs();
      return;
    }
    request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        that.setData({ joined: res.data.joined_clubs || [] });
      },
      complete() {
        that.fetchClubs();
      }
    });
  },
  fetchClubs() {
    const that = this;
    const uid = store.userId;
    request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        let list = res.data;
        const q = that.data.query;
        if (q) {
          list = list.filter(c => c.name.includes(q) || c.club_id.includes(q));
        }
        if (!list.length) {
          that.setData({ clubs: [] });
          return;
        }
        const ids = list.map(c => c.club_id).join(',');
        request({
          url: `${BASE_URL}/clubs/batch?club_ids=${ids}`,
          success(r) {
            const infos = r.data || [];
            const result = infos.map(info =>
              formatJoinClubCardData(info, uid, that.data.joined)
            );
            that.setData({ clubs: result });
            if (that.data.directClubId) {
              const target = result.find(c => c.club_id === that.data.directClubId);
              if (target) {
                that.join({ detail: { club: target } });
              }
              that.setData({ directClubId: '' });
            }
          }
        });
      }
    });
  },
  join(e) {
    const cid = e.detail.club ? e.detail.club.club_id : '';
    const userId = store.userId;
    const token = store.token;
    const that = this;
    if (!userId || !token) return;
    request({
      url: `${BASE_URL}/users/${userId}`,
      success(res) {
        const limit =
          res.data.max_joinable_clubs != null ? res.data.max_joinable_clubs : 5;
        if (res.data.joined_clubs && res.data.joined_clubs.length >= limit) {
          wx.showToast({ duration: 4000,  title: that.data.t.joinLimitReached, icon: 'none' });
          return;
        }
        request({
          url: `${BASE_URL}/players/${userId}`,
          success(pres) {
            const info = pres.data || {};
            const need =
              info.singles_rating == null && info.doubles_rating == null;
              that.setData({
                showDialog: true,
                joinClubId: cid,
                needRating: need,
                rating: '',
                reason: ''
              });
          }
        });
      }
    });
  },
  onRating(e) {
    this.setData({ rating: e.detail.value });
  },
  onReason(e) {
    this.setData({ reason: e.detail.value });
  },
  cancelJoin() {
    this.setData({ showDialog: false });
  },
  hideKeyboard,
  noop() {},
  viewReject(e) {
    const reason = e.detail.reason || '';
    const cid = e.detail.club ? e.detail.club.club_id : '';
    const uid = store.userId;
    const token = store.token;
    const that = this;
    wx.showModal({
      title: that.data.t.rejectReason || '未通过原因',
      content: reason || '',
      showCancel: false,
      confirmText: that.data.t.acknowledge || '了解',
      success() {
        request({
          url: `${BASE_URL}/clubs/${cid}/clear_rejection`,
          method: 'POST',
          data: { user_id: uid, token },
          complete() {
            that.fetchJoined();
          }
        });
      }
    });
  },
  submitJoin() {
    const userId = store.userId;
    const token = store.token;
    const cid = this.data.joinClubId;
    const rating = parseFloat(this.data.rating);
    if (
      (this.data.needRating && (isNaN(rating) || rating < 0 || rating > 7)) ||
      !this.data.reason
    ) {
      wx.showToast({ duration: 4000,  title: that.data.t.incompleteInfo, icon: 'none' });
      return;
    }
    const that = this;
    ensureSubscribe('club_join').then(() => {
      request({
        url: `${BASE_URL}/clubs/${cid}/join`,
        method: 'POST',
        data: {
          user_id: userId,
          token,
          singles_rating: this.data.needRating ? rating : undefined,
          doubles_rating: this.data.needRating ? rating : undefined,
          reason: this.data.reason
        },
        success(r) {
          if (r.statusCode === 200) {
            store.setClubId(cid);
            wx.showToast({ duration: 4000,  title: that.data.t.applied, icon: 'success' });
            const clubs = that.data.clubs.map(c =>
              c.club_id === cid ? { ...c, pending: true, rejected_reason: '' } : c
            );
            that.setData({ clubs, showDialog: false });
          } else {
            wx.showToast({ duration: 4000,  title: that.data.t.failed, icon: 'none' });
          }
        }
      });
    });
  }
});
