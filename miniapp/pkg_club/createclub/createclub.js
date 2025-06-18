const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const store = require('../../store/store');
const {
  showError,
  validateClubName,
  validateRating
} = require('../../utils/validator');

Page({
  data: {
    t: zh_CN,
    name: '',
    nameError: '',
    slogan: '',
    logo: '',
    region: [],
    regionString: '',
    showDialog: false,
    rating: ''
  },
  onName(e) {
    const name = e.detail.value;
    const ok = /^[A-Za-z\u4e00-\u9fa5]{0,20}$/.test(name);
    this.setData({ name, nameError: ok ? '' : this.data.t.clubNameRule });
  },
  onSlogan(e) { this.setData({ slogan: e.detail.value }); },
  onRegionChange(e) {
    this.setData({
      region: e.detail.value,
      regionString: e.detail.value.join(' ')
    });
  },
  onRating(e) {
    this.setData({ rating: e.detail.value });
  },
  cancelRating() {
    this.setData({ showDialog: false });
  },
  hideKeyboard,
  confirmRating() {
    const rating = validateRating(this.data.rating);
    if (rating == null) return;
    this.setData({ showDialog: false });
    this.createClub(rating);
  },
  createClub(initialRating) {
    const userId = store.userId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs`,
      method: 'POST',
      data: {
        name: this.data.name,
        logo: this.data.logo,
        region: this.data.regionString,
        slogan: this.data.slogan,
        user_id: userId,
        token
      },
      success(res) {
        if (res.statusCode === 200) {
          const cid = res.data.club_id;
          if (initialRating != null) {
            request({
              url: `${BASE_URL}/clubs/${cid}/prerate`,
              method: 'POST',
              data: {
                rater_id: userId,
                target_id: userId,
                rating: initialRating,
                token
              },
              complete() {
                wx.showToast({ title: that.data.t.created, icon: 'success' });
                wx.navigateBack();
              }
            });
          } else {
            wx.showToast({ title: that.data.t.created, icon: 'success' });
            wx.navigateBack();
          }
        } else {
          const msg = (res.data && res.data.detail) || that.data.t.failed;
          wx.showToast({ title: msg, icon: 'none' });
        }
      }
    });
  },
  chooseLogo() {
    const that = this;
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      success(res) {
        that.setData({ logo: res.tempFilePaths[0] });
      }
    });
  },
  submit() {
    const that = this;
    const userId = store.userId;
    const token = store.token;
    if (!userId || !token || !this.data.name || !this.data.slogan || this.data.region.length === 0) {
      showError(that.data.t.incompleteInfo);
      return;
    }
    if (!validateClubName(this.data.name)) return;
    request({
      url: `${BASE_URL}/players/${userId}`,
      success(res) {
        const info = res.data || {};
        const need = info.singles_rating == null && info.doubles_rating == null;
        if (need) {
          that.setData({ showDialog: true, rating: '' });
        } else {
          that.createClub();
        }
      },
      fail() {
        wx.showToast({ title: that.data.t.loadFailed, icon: 'none' });
      }
    });
  },
  noop() {}
});
