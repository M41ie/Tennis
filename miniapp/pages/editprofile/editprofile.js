const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    name: '',
    gender: '',
    avatar: '',
    birth: '',
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
          gender: p.gender || '',
          avatar: p.avatar || ''
        });
      }
    });
  },
  onName(e) { this.setData({ name: e.detail.value }); },
  onGender(e) { this.setData({ gender: e.detail.value }); },
  onBirthChange(e) { this.setData({ birth: e.detail.value }); },
  chooseAvatar() {
    const that = this;
    wx.chooseImage({
      count: 1,
      success(res) {
        that.setData({ avatar: res.tempFilePaths[0] });
      }
    });
  },
  submit() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    if (!cid || !token || !this.data.userId) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${this.data.userId}`,
      method: 'PATCH',
      data: {
        user_id: this.data.userId,
        token,
        name: this.data.name,
        gender: this.data.gender,
        avatar: this.data.avatar,
        birth: this.data.birth
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
