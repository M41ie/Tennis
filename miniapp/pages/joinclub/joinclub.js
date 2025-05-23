Page({
  data: {
    clubs: [],
    query: ''
  },
  onLoad() {
    this.fetchClubs();
  },
  onSearch(e) {
    this.setData({ query: e.detail.value });
    this.fetchClubs();
  },
  fetchClubs() {
    const that = this;
    wx.request({
      url: 'http://localhost:8000/clubs',
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
      url: `http://localhost:8000/users/${userId}`,
      success(res) {
        if (res.data.joined_clubs && res.data.joined_clubs.length >= 5) {
          wx.showToast({ title: 'Limit reached', icon: 'none' });
          return;
        }
        wx.request({
          url: `http://localhost:8000/clubs/${cid}/join`,
          method: 'POST',
          data: { user_id: userId, token },
          success(r) {
            if (r.statusCode === 200) {
              wx.setStorageSync('club_id', cid);
              wx.showToast({ title: 'Joined', icon: 'success' });
            } else {
              wx.showToast({ title: 'Failed', icon: 'none' });
            }
          }
        });
      }
    });
  }
});
