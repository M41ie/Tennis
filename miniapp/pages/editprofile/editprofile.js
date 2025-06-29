const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const store = require('../../store/store');
const { genderText } = require('../../utils/userFormat');
const {
  showError,
  validateUserName
} = require('../../utils/validator');

Page({
  data: {
    t: zh_CN,
    name: '',
    nameError: '',
    genderIndex: 0,
    avatar: '',
    tempAvatar: '',
    birth: '',
    handIndex: 0,
    backhandIndex: 0,
    region: [],
    regionString: '',
    genderOptions: ['请选择', '男', '女'],
    handOptions: ['请选择', '右手持拍', '左手持拍'],
    backhandOptions: ['请选择', '双反', '单反'],
    userId: '',
    submitting: false
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
        const gText = genderText(p.gender);
        if (gText === '男') gIndex = 1;
        if (gText === '女') gIndex = 2;
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
  onName(e) {
    const name = e.detail.value;
    const ok = /^[A-Za-z\u4e00-\u9fa5]{0,12}$/.test(name);
    this.setData({ name, nameError: ok ? '' : this.data.t.nameRule });
  },
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
      sizeType: ['compressed'],
      success(res) {
        const path = res.tempFilePaths[0];
        if (!/\.(jpg|jpeg|png)$/i.test(path)) {
          wx.showToast({ duration: 4000,  title: that.data.t.uploadImageError, icon: 'none' });
          return;
        }
        that.setData({ avatar: path, tempAvatar: path });
      }
    });
  },
  submit() {
    const that = this;
    const token = store.token;
    if (!token || !this.data.userId) return;
    if (this.data.submitting) return;
    const incomplete =
      !this.data.name ||
      this.data.genderIndex === 0 ||
      !this.data.birth ||
      this.data.handIndex === 0 ||
      this.data.backhandIndex === 0 ||
      !this.data.regionString;
    if (incomplete) {
      showError(that.data.t.incompleteInfo);
      return;
    }
    if (!validateUserName(this.data.name)) return;
    this.setData({ submitting: true });

    const doRequest = () => {
      request({
        url: `${BASE_URL}/players/${that.data.userId}`,
        method: 'PUT',
        data: {
          user_id: that.data.userId,
          token,
          name: that.data.name,
          gender: that.data.genderIndex === 1 ? 'M' : that.data.genderIndex === 2 ? 'F' : '',
          avatar: that.data.avatar,
          birth: that.data.birth,
          handedness: that.data.handOptions[that.data.handIndex] || '',
          backhand: that.data.backhandOptions[that.data.backhandIndex] || '',
          region: that.data.regionString
        },
        success(res) {
          if (res.statusCode === 200) {
            wx.showToast({ duration: 4000,  title: that.data.t.updated, icon: 'success' });
            wx.navigateBack();
          } else {
            wx.showToast({ duration: 4000,  title: that.data.t.failed, icon: 'none' });
          }
        },
        complete() {
          that.setData({ submitting: false });
        }
      });
    };

    if (this.data.tempAvatar && /^wxfile:/.test(this.data.tempAvatar)) {
      wx.showLoading({ title: this.data.t.loading, mask: true });
      wx.uploadFile({
        url: `${BASE_URL}/upload`,
        filePath: this.data.tempAvatar,
        name: 'file',
        success(resp) {
          let data = {};
          try {
            data = JSON.parse(resp.data);
          } catch (e) {}
          if (data && data.url) {
            that.setData({ avatar: data.url, tempAvatar: data.url });
            doRequest();
          } else {
            wx.showToast({ duration: 4000,  title: that.data.t.failed, icon: 'none' });
            that.setData({ submitting: false });
          }
        },
        fail() {
          wx.showToast({ duration: 4000,  title: that.data.t.failed, icon: 'none' });
          that.setData({ submitting: false });
        },
        complete() {
          wx.hideLoading();
        }
      });
    } else {
      doRequest();
    }
  }
});
