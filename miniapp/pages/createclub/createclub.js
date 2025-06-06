const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubId: '',
    name: '',
    logo: '',
    region: ''
  },
  onClubId(e) { this.setData({ clubId: e.detail.value }); },
  onName(e) { this.setData({ name: e.detail.value }); },
  onRegion(e) { this.setData({ region: e.detail.value }); },
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
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    if (!userId || !token || !this.data.clubId || !this.data.name) {
      wx.showToast({ title: '信息不完整', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs`,
      method: 'POST',
      data: {
        club_id: this.data.clubId,
        name: this.data.name,
        logo: this.data.logo,
        region: this.data.region,
        user_id: userId,
        token
      },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ title: '已创建', icon: 'success' });
          wx.navigateBack();
        } else {
          const msg = (res.data && res.data.detail) || 'Failed';
          wx.showToast({ title: msg, icon: 'none' });
        }
      }
    });
  }
});
