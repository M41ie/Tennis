const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const store = require('../../store/store');

Page({
  data: {
    t: zh_CN,
    name: '',
    slogan: '',
    logo: '',
    region: [],
    regionString: ''
  },
  onLoad() {
    const cid = store.clubId;
    if (!cid) return;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data || {};
        const regionStr = info.region || '';
        that.setData({
          name: info.name || '',
          slogan: info.slogan || '',
          logo: info.logo || '',
          region: regionStr ? regionStr.split(' ') : [],
          regionString: regionStr
        });
      }
    });
  },
  onName(e) { this.setData({ name: e.detail.value }); },
  onSlogan(e) { this.setData({ slogan: e.detail.value }); },
  onRegionChange(e) {
    this.setData({
      region: e.detail.value,
      regionString: e.detail.value.join(' ')
    });
  },
  hideKeyboard,
  chooseLogo() {
    const that = this;
    wx.chooseImage({
      count: 1,
      success(res) {
        that.setData({ logo: res.tempFilePaths[0] });
      }
    });
  },
  submit() {
    const cid = store.clubId;
    const userId = store.userId;
    const token = store.token;
    if (!cid || !userId || !token) return;
    if (!this.data.name || !this.data.slogan || this.data.region.length === 0) {
      wx.showToast({ title: that.data.t.incompleteInfo, icon: 'none' });
      return;
    }
    const nameOk = /^[A-Za-z\u4e00-\u9fa5]{1,20}$/.test(this.data.name);
    if (!nameOk) {
      wx.showToast({ title: that.data.t.clubNameRule, icon: 'none' });
      return;
    }
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}`,
      method: 'PATCH',
      data: {
        user_id: userId,
        token,
        name: this.data.name,
        logo: this.data.logo,
        region: this.data.regionString,
        slogan: this.data.slogan
      },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ title: that.data.t.updated, icon: 'success' });
          wx.navigateBack();
        } else {
          const msg = (res.data && res.data.detail) || that.data.t.failed;
          wx.showToast({ title: msg, icon: 'none' });
        }
      }
    });
  }
});
