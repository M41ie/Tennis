const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [],
    query: ''
  },
  onLoad(options) {
    if (options && options.query) {
      this.setData({ query: options.query });
    }
    this.fetchClubs();
  },
  onSearch(e) {
    this.setData({ query: e.detail.value });
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        let list = res.data;
        const q = that.data.query;
        if (q) {
          list = list.filter(c => c.name.includes(q) || c.club_id.includes(q));
        }
        that.setData({ clubs: list });
      }
    });
  },
  join(e) {
    const cid = e.currentTarget.dataset.id;
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!userId || !token) return;
    wx.request({
      url: `${BASE_URL}/users/${userId}`,
      success(res) {
        if (res.data.joined_clubs && res.data.joined_clubs.length >= 5) {
          wx.showToast({ title: '达到上限', icon: 'none' });
          return;
        }
        wx.request({
          url: `${BASE_URL}/clubs/${cid}/join`,
          method: 'POST',
          data: { user_id: userId, token },
          success(r) {
            if (r.statusCode === 200) {
              wx.setStorageSync('club_id', cid);
              wx.showToast({ title: '已加入', icon: 'success' });
            } else {
              wx.showToast({ title: '失败', icon: 'none' });
            }
          }
        });
      }
    });
  },
  createClub() {
    wx.navigateTo({ url: '/pages/createclub/createclub' });
  }
});
