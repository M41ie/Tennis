const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../services/api');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const store = require('../../store/store');

Page({
  data: {
    t: zh_CN,
    name: '',
    genderIndex: 0,
    avatar: '',
    birth: '',
    handIndex: 0,
    backhandIndex: 0,
    region: [],
    regionString: '',
    genderOptions: ['请选择', '男', '女'],
    handOptions: ['请选择', '右手持拍', '左手持拍'],
    backhandOptions: ['请选择', '双反', '单反'],
    userId: ''
  },
  onLoad() {
    const uid = store.userId;
    if (!uid) return;
    this.setData({ userId: uid });
    const that = this;
    request({
      url: `${BASE_URL}/players/${uid}`,
      success(res) {
        const p = res.data || {};
        let gIndex = 0;
        if (p.gender === 'M' || p.gender === '男' || p.gender === 'Male') gIndex = 1;
        if (p.gender === 'F' || p.gender === '女' || p.gender === 'Female') gIndex = 2;
        const regionArr = p.region ? p.region.split(/[\s-]+/) : [];
        that.setData({
          name: p.name || '',
          genderIndex: gIndex,
          handIndex: that.data.handOptions.indexOf(p.handedness) > -1 ? that.data.handOptions.indexOf(p.handedness) : 0,
          backhandIndex: that.data.backhandOptions.indexOf(p.backhand) > -1 ? that.data.backhandOptions.indexOf(p.backhand) : 0,
          avatar: p.avatar || '',
          birth: p.birth || '',
          region: regionArr,
          regionString: p.region || ''
        });
      }
    });
  },
  onName(e) { this.setData({ name: e.detail.value }); },
  onGender(e) { this.setData({ genderIndex: Number(e.detail.value) }); },
  onBirthChange(e) { this.setData({ birth: e.detail.value }); },
  onHand(e) { this.setData({ handIndex: Number(e.detail.value) }); },
  onBackhand(e) { this.setData({ backhandIndex: Number(e.detail.value) }); },
  onRegionChange(e) {
    this.setData({
      region: e.detail.value,
      regionString: e.detail.value.join(' ')
    });
  },
  hideKeyboard,
  chooseAvatar() {
    const that = this;
    wx.chooseImage({
      count: 1,
      success(res) {
        const path = res.tempFilePaths[0];
        if (!/\.(jpg|jpeg|png)$/i.test(path)) {
          wx.showToast({ title: that.data.t.uploadImageError, icon: 'none' });
          return;
        }
        that.setData({ avatar: path });
      }
    });
  },
  submit() {
    const token = store.token;
    if (!token || !this.data.userId) return;
    const incomplete =
      !this.data.name ||
      this.data.genderIndex === 0 ||
      !this.data.birth ||
      this.data.handIndex === 0 ||
      this.data.backhandIndex === 0 ||
      !this.data.regionString;
    if (incomplete) {
      wx.showToast({ title: that.data.t.incompleteInfo, icon: 'none' });
      return;
    }
    const nameOk = /^[A-Za-z\u4e00-\u9fa5]{1,12}$/.test(this.data.name);
    if (!nameOk) {
      wx.showToast({ title: that.data.t.nameRule, icon: 'none' });
      return;
    }
    const that = this;
    request({
      url: `${BASE_URL}/players/${this.data.userId}`,
      method: 'PATCH',
      data: {
        user_id: this.data.userId,
        token,
        name: this.data.name,
        gender: this.data.genderIndex === 1 ? 'M' : this.data.genderIndex === 2 ? 'F' : '',
        avatar: this.data.avatar,
        birth: this.data.birth,
        handedness: this.data.handOptions[this.data.handIndex] || '',
        backhand: this.data.backhandOptions[this.data.backhandIndex] || '',
        region: this.data.regionString
      },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ title: that.data.t.updated, icon: 'success' });
          wx.navigateBack();
        } else {
          wx.showToast({ title: that.data.t.failed, icon: 'none' });
        }
      }
    });
  }
});
