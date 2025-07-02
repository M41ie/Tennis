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
const uploadAvatar = require('../../utils/upload');
const userService = require('../../services/user');

function ensureSlash(p) {
  return p.startsWith('/') ? p : '/' + p;
}

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
    submitting: false,
    form: {},
    newAvatarTempPath: ''
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
          regionString: p.region || '',
          form: { ...p }
        });
      }
    });
  },
  onName(e) {
    const name = e.detail.value;
    const ok = /^[A-Za-z\u4e00-\u9fa5]{0,12}$/.test(name);
    this.setData({ name, nameError: ok ? '' : this.data.t.nameRule, 'form.name': name });
  },
  onGender(e) {
    const idx = Number(e.detail.value);
    this.setData({ genderIndex: idx, 'form.gender': idx === 1 ? 'M' : idx === 2 ? 'F' : '' });
  },
  onBirthChange(e) { this.setData({ birth: e.detail.value, 'form.birth': e.detail.value }); },
  onHand(e) {
    const idx = Number(e.detail.value);
    this.setData({ handIndex: idx, 'form.handedness': this.data.handOptions[idx] || '' });
  },
  onBackhand(e) {
    const idx = Number(e.detail.value);
    this.setData({ backhandIndex: idx, 'form.backhand': this.data.backhandOptions[idx] || '' });
  },
  onRegionChange(e) {
    this.setData({
      region: e.detail.value,
      regionString: e.detail.value.join(' '),
      'form.region': e.detail.value.join(' ')
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
        that.setData({
          avatar: path,
          tempAvatar: path,
          'form.avatar': path,
          newAvatarTempPath: path
        });
      }
    });
  },
  async submit() {
    const token = store.token;
    if (!token || !this.data.userId) {
      wx.showToast({ duration: 4000, title: this.data.t.pleaseRelogin, icon: 'none' });
      return;
    }
    if (this.data.submitting) return;
    const incomplete =
      !this.data.name ||
      this.data.genderIndex === 0 ||
      !this.data.birth ||
      this.data.handIndex === 0 ||
      this.data.backhandIndex === 0 ||
      !this.data.regionString;
    if (incomplete) {
      showError(this.data.t.incompleteInfo);
      return;
    }
    if (!validateUserName(this.data.name)) return;

    this.setData({ submitting: true });
    wx.showLoading({ title: this.data.t.loading, mask: true });

    try {
      let finalPayload = {
        user_id: this.data.userId,
        name: this.data.name,
        gender: this.data.genderIndex === 1 ? 'M' : this.data.genderIndex === 2 ? 'F' : '',
        birth: this.data.birth,
        handedness: this.data.handOptions[this.data.handIndex] || '',
        backhand: this.data.backhandOptions[this.data.backhandIndex] || '',
        region: this.data.regionString,
        avatar: this.data.avatar
      };

      if (this.data.newAvatarTempPath) {
        const permanentRelativeUrl = await uploadAvatar(this.data.newAvatarTempPath);
        finalPayload.avatar = ensureSlash(permanentRelativeUrl);
        this.setData({
          avatar: ensureSlash(permanentRelativeUrl),
          'form.avatar': ensureSlash(permanentRelativeUrl)
        });
      }

      // ======================= 新增的诊断代码在这里 =======================
      // 在发起更新请求前，以易于阅读的JSON格式打印出将要发送的完整对象
      console.log('【最终诊断】发送给后端的用户资料 payload:', JSON.stringify(finalPayload, null, 2));
      // =================================================================
      
      await userService.updatePlayerProfile(this.data.userId, finalPayload);

      wx.showToast({ duration: 4000,  title: this.data.t.updated, icon: 'success' });
      store.fetchUserInfo && store.fetchUserInfo();
      wx.navigateBack();
    } catch (e) {
      wx.showToast({ duration: 4000,  title: this.data.t.failed, icon: 'none' });
    } finally {
      this.setData({ submitting: false, newAvatarTempPath: '' });
      wx.hideLoading();
    }
  }
});
