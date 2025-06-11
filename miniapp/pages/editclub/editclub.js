const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    name: '',
    slogan: '',
    logo: '',
    region: [],
    regionString: ''
  },
  onLoad() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    if (!cid || !userId || !token) return;
    if (!this.data.name || !this.data.slogan || this.data.region.length === 0) {
      wx.showToast({ title: '信息不完整', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
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
          wx.showToast({ title: '已更新', icon: 'success' });
          wx.navigateBack();
        } else {
          const msg = (res.data && res.data.detail) || '失败';
          wx.showToast({ title: msg, icon: 'none' });
        }
      }
    });
  }
});
