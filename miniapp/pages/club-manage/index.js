const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    query: '',
    searchResults: [],
    myClubs: []
  },
  onLoad() {
    this.getMyClubs();
  },
  onSearch(e) {
    this.setData({ query: e.detail.value });
    this.searchClubs();
  },
  searchClubs() {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs`,
      data: { search: this.data.query },
      success(res) {
        that.setData({ searchResults: res.data || [] });
      }
    });
  },
  joinClub(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!uid || !token) return;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/join`,
      method: 'POST',
      data: { user_id: uid, token },
      complete() {
        that.searchClubs();
        that.getMyClubs();
      }
    });
  },
  getMyClubs() {
    const uid = wx.getStorageSync('user_id');
    if (!uid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const ids = res.data.joined_clubs || [];
        if (!ids.length) {
          that.setData({ myClubs: [] });
          return;
        }
        const list = [];
        let count = 0;
        ids.forEach(cid => {
          wx.request({
            url: `${BASE_URL}/clubs/${cid}`,
            success(r) {
              const info = r.data;
              let role = 'member';
              if (info.leader_id === uid) role = 'leader';
              else if (info.admin_ids && info.admin_ids.includes(uid)) role = 'admin';
              list.push({ club_id: cid, name: info.name, role });
            },
            complete() {
              count++;
              if (count === ids.length) {
                that.setData({ myClubs: list });
              }
            }
          });
        });
      }
    });
  },
  openClub(e) {
    const cid = e.currentTarget.dataset.id;
    if (cid) {
      wx.setStorageSync('club_id', cid);
      wx.navigateTo({ url: '/pages/manage/manage' });
    }
  },
  quitClub(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'quit' },
      complete() { that.getMyClubs(); }
    });
  },
  resignAdmin(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'resign_admin' },
      complete() { that.getMyClubs(); }
    });
  },
  toggleAdmin(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'toggle_admin' },
      complete() { that.getMyClubs(); }
    });
  },
  transferLeader(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'transfer_leader' },
      complete() { that.getMyClubs(); }
    });
  }
});
