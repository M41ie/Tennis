const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    name: '',
    slogan: '',
    logo: '',
    region: [],
    regionString: '',
    showDialog: false,
    rating: ''
  },
  onName(e) { this.setData({ name: e.detail.value }); },
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
  hideKeyboard() {
    wx.hideKeyboard();
  },
  confirmRating() {
    const rating = parseFloat(this.data.rating);
    if (isNaN(rating) || rating < 0 || rating > 7) {
      wx.showToast({ title: '评分格式错误', icon: 'none' });
      return;
    }
    this.setData({ showDialog: false });
    this.createClub(rating);
  },
  createClub(initialRating) {
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
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
            wx.request({
              url: `${BASE_URL}/clubs/${cid}/prerate`,
              method: 'POST',
              data: {
                rater_id: userId,
                target_id: userId,
                rating: initialRating,
                token
              },
              complete() {
                wx.showToast({ title: '已创建', icon: 'success' });
                wx.navigateBack();
              }
            });
          } else {
            wx.showToast({ title: '已创建', icon: 'success' });
            wx.navigateBack();
          }
        } else {
          const msg = (res.data && res.data.detail) || 'Failed';
          wx.showToast({ title: msg, icon: 'none' });
        }
      }
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
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    if (!userId || !token || !this.data.name || !this.data.slogan || this.data.region.length === 0) {
      wx.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }
    const nameOk = /^[A-Za-z\u4e00-\u9fa5]{1,20}$/.test(this.data.name);
    if (!nameOk) {
      wx.showToast({ title: '俱乐部名格式错误', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
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
        wx.showToast({ title: '获取信息失败', icon: 'none' });
      }
    });
  },
  noop() {}
});
