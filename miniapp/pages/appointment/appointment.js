const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    appointments: [],
    date: '',
    location: ''
  },
  onLoad() {
    this.fetch();
  },
  fetch() {
    const cid = wx.getStorageSync('club_id');
    const that = this;
    if (!cid) return;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/appointments`,
      success(res) {
        that.setData({ appointments: res.data });
      }
    });
  },
  onDate(e) { this.setData({ date: e.detail.value }); },
  onLocation(e) { this.setData({ location: e.detail.value }); },
  create() {
    const cid = wx.getStorageSync('club_id');
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!cid || !userId || !token) return;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/appointments`,
      method: 'POST',
      data: { user_id: userId, date: this.data.date, location: this.data.location, token },
      success() { that.fetch(); }
    });
  },
  signup(e) {
    const idx = e.currentTarget.dataset.idx;
    const cid = wx.getStorageSync('club_id');
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/appointments/${idx}/signup`,
      method: 'POST',
      data: { user_id: userId, token },
      success() { that.fetch(); }
    });
  },
  cancel(e) {
    const idx = e.currentTarget.dataset.idx;
    const cid = wx.getStorageSync('club_id');
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/appointments/${idx}/cancel`,
      method: 'POST',
      data: { user_id: userId, token },
      success() { that.fetch(); }
    });
  }
});
