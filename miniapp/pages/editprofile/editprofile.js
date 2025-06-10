const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    name: '',
    genderIndex: 0,
    avatar: '',
    birth: '',
    handIndex: 0,
    backhandIndex: 0,
    genderOptions: ['请选择', '男', '女'],
    handOptions: ['请选择', '右手持拍', '左手持拍'],
    backhandOptions: ['请选择', '双反', '单反'],
    userId: ''
  },
  onLoad() {
    const uid = wx.getStorageSync('user_id');
    const cid = wx.getStorageSync('club_id');
    if (!uid || !cid) return;
    this.setData({ userId: uid });
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${uid}`,
      success(res) {
        const p = res.data || {};
        that.setData({
          name: p.name || '',
          genderIndex: that.data.genderOptions.indexOf(p.gender) > -1 ? that.data.genderOptions.indexOf(p.gender) : 0,
          handIndex: that.data.handOptions.indexOf(p.handedness) > -1 ? that.data.handOptions.indexOf(p.handedness) : 0,
          backhandIndex: that.data.backhandOptions.indexOf(p.backhand) > -1 ? that.data.backhandOptions.indexOf(p.backhand) : 0,
          avatar: p.avatar || '',
          birth: p.birth || ''
        });
      }
    });
  },
  onName(e) { this.setData({ name: e.detail.value }); },
  onGender(e) { this.setData({ genderIndex: Number(e.detail.value) }); },
  onBirthChange(e) { this.setData({ birth: e.detail.value }); },
  onHand(e) { this.setData({ handIndex: Number(e.detail.value) }); },
  onBackhand(e) { this.setData({ backhandIndex: Number(e.detail.value) }); },
  chooseAvatar() {
    const that = this;
    wx.chooseImage({
      count: 1,
      success(res) {
        const path = res.tempFilePaths[0];
        if (!/\.(jpg|jpeg|png)$/i.test(path)) {
          wx.showToast({ title: '请上传 jpg/png 图片', icon: 'none' });
          return;
        }
        that.setData({ avatar: path });
      }
    });
  },
  submit() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    if (!cid || !token || !this.data.userId) return;
    const nameOk = /^[A-Za-z0-9\u4e00-\u9fa5]{1,20}$/.test(this.data.name);
    if (!nameOk) {
      wx.showToast({ title: '用户名格式错误', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${this.data.userId}`,
      method: 'PATCH',
      data: {
        user_id: this.data.userId,
        token,
        name: this.data.name,
        gender: this.data.genderOptions[this.data.genderIndex] || '',
        avatar: this.data.avatar,
        birth: this.data.birth,
        handedness: this.data.handOptions[this.data.handIndex] || '',
        backhand: this.data.backhandOptions[this.data.backhandIndex] || ''
      },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ title: '已更新', icon: 'success' });
          wx.navigateBack();
        } else {
          wx.showToast({ title: '失败', icon: 'none' });
        }
      }
    });
  }
});
