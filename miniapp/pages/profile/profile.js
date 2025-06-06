const BASE_URL = getApp().globalData.BASE_URL;
const IMAGES = require('../../assets/base64.js');

Page({
  data: {
    loggedIn: false,
    user: null,
    records: [],
    loginId: '',
    loginPw: '',
    isSelf: false,
    clubId: '',
    joinedClubs: [],
    unreadCount: 0,
    genders: ['M', 'F'],
    genderIndex: 0,
    editing: false,
    placeholderAvatar: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/5+BMwAIAwGRAAGuIwVxAAAAAElFTkSuQmCC',
    loginPlaceholder: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/5+BMwAIAwGRAAGuIwVxAAAAAElFTkSuQmCC',
    iconClub: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/5+BMwAIAwGRAAGuIwVxAAAAAElFTkSuQmCC',
    iconComing: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/5+BMwAIAwGRAAGuIwVxAAAAAElFTkSuQmCC'
  },
  onShow() {
    const uid = wx.getStorageSync('user_id');
    const cid = wx.getStorageSync('club_id');
    if (uid) {
      this.setData({ loggedIn: true, isSelf: true });
      this.fetchJoined(uid, cid);
      this.fetchUnread();
    } else {
      this.setData({ loggedIn: false, user: null });
    }
  },
  onLoad(options) {
    const userId = options.id || wx.getStorageSync('user_id');
    const cid = options.cid || wx.getStorageSync('club_id');
    if (userId) {
      this.setData({ isSelf: userId === wx.getStorageSync('user_id') });
      this.fetchJoined(userId, cid);
    }
  },
  onCardTap() {
    if (!this.data.loggedIn) {
      wx.navigateTo({ url: '/pages/login/index' });
    }
  },
  goClub() {
    wx.navigateTo({ url: '/pages/club-manage/index' });
  },
  onUserId(e) { this.setData({ loginId: e.detail.value }); },
  onPassword(e) { this.setData({ loginPw: e.detail.value }); },
  login() {
    if (!this.data.loginId || !this.data.loginPw) {
      wx.showToast({ title: '信息不完整', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
      url: `${BASE_URL}/login`,
      method: 'POST',
      data: { user_id: this.data.loginId, password: this.data.loginPw },
      timeout: 5000,
      success(res) {
        if (res.data.success) {
          wx.setStorageSync('token', res.data.token);
          wx.setStorageSync('user_id', that.data.loginId);
          const cid = wx.getStorageSync('club_id');
          if (cid) {
            that.setData({ isSelf: true, clubId: cid });
            that.fetchUser(cid, that.data.loginId);
          }
          that.fetchUnread();
        } else {
          wx.showToast({ title: '登录失败', icon: 'none' });
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
  },
  wechatLogin() {
    const that = this;
    wx.login({
      success(res) {
        if (!res.code) return;
        wx.request({
          url: `${BASE_URL}/wechat_login`,
          method: 'POST',
          data: { code: res.code },
          timeout: 5000,
          success(resp) {
            if (resp.statusCode === 200 && resp.data.token) {
              wx.setStorageSync('token', resp.data.token);
              wx.setStorageSync('user_id', resp.data.user_id);
              const cid = wx.getStorageSync('club_id');
              if (cid) {
                that.setData({ isSelf: true, clubId: cid });
                that.fetchUser(cid, resp.data.user_id);
              }
              that.fetchUnread();
            } else {
              wx.showToast({ title: '登录失败', icon: 'none' });
            }
          },
          fail() {
            wx.showToast({ title: '网络错误', icon: 'none' });
          }
        });
      }
    });
  },
  fetchJoined(id, cid) {
    const that = this;
    wx.request({
      url: `${BASE_URL}/users/${id}`,
      success(res) {
        const list = res.data.joined_clubs || [];
        let current = cid;
        if (!current && list.length) {
          current = list[0];
          wx.setStorageSync('club_id', current);
        }
        that.setData({ joinedClubs: list, clubId: current || '' });
        if (current) {
          that.fetchUser(current, id);
        }
      }
    });
  },
  fetchUser(cid, id) {
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${id}?recent=5`,
      success(res) {
        const idx = that.data.genders.indexOf(res.data.gender);
        const userData = res.data;
        if (userData.singles_rating != null)
          userData.singles_rating = userData.singles_rating.toFixed(3);
        if (userData.doubles_rating != null)
          userData.doubles_rating = userData.doubles_rating.toFixed(3);
        if (userData.recent_records) {
          userData.recent_records.forEach(r => {
            if (r.self_rating_after != null)
              r.self_rating_after = r.self_rating_after.toFixed(3);
          });
        }
        that.setData({
          user: userData,
          records: userData.recent_records || [],
          genderIndex: idx >= 0 ? idx : 0
        });
      }
    });
  },
  fetchUnread() {
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!uid || !token) return;
    wx.request({
      url: `${BASE_URL}/users/${uid}/messages/unread_count?token=${token}`,
      success(res) {
        that.setData({ unreadCount: res.data.unread });
      }
    });
  },
  onAge(e) {
    this.setData({ 'user.age': parseInt(e.detail.value) || null });
  },
  onGender(e) {
    this.setData({ 'user.gender': e.detail.value });
  },
  onName(e) {
    this.setData({ 'user.name': e.detail.value });
  },
  chooseAvatar() {
    const that = this;
    wx.chooseImage({
      count: 1,
      success(res) {
        that.setData({ 'user.avatar': res.tempFilePaths[0] });
      }
    });
  },
  startEdit() {
    this.setData({ editing: true });
  },
  cancelEdit() {
    this.setData({ editing: false });
    const cid = this.data.clubId;
    const uid = this.data.user ? this.data.user.user_id : wx.getStorageSync('user_id');
    if (cid && uid) {
      this.fetchUser(cid, uid);
    }
  },
  saveProfile() {
    this.updateProfile();
    this.setData({ editing: false });
  },
  updateProfile() {
    const cid = this.data.clubId;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!cid || !uid || !token) return;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${uid}`,
      method: 'PATCH',
      data: {
        user_id: uid,
        token,
        name: this.data.user.name,
        age: this.data.user.age,
        gender: this.data.user.gender,
        avatar: this.data.user.avatar
      },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ title: '已更新', icon: 'success' });
          that.fetchUser(cid, uid);
        } else {
          wx.showToast({ title: '失败', icon: 'none' });
        }
      }
    });
  },
  manageClubs() {
    wx.navigateTo({ url: '/pages/joinclub/joinclub' });
  },
  toRegister() {
    wx.navigateTo({ url: '/pages/register/register' });
  },
  manageMembers() {
    wx.navigateTo({ url: '/pages/manage/manage' });
  },
  viewMessages() {
    wx.navigateTo({ url: '/pages/messages/messages' });
  },
  toPrerate() {
    wx.navigateTo({ url: '/pages/prerate/prerate' });
  },
  selectClub(e) {
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    if (cid && uid) {
      wx.setStorageSync('club_id', cid);
      this.setData({ clubId: cid });
      this.fetchUser(cid, uid);
    }
  },
  logout() {
    const token = wx.getStorageSync('token');
    const that = this;
    if (token) {
      wx.request({
        url: `${BASE_URL}/logout`,
        method: 'POST',
        data: { token },
        complete() {
          wx.removeStorageSync('token');
          wx.removeStorageSync('user_id');
          wx.removeStorageSync('club_id');
          that.setData({ loggedIn: false, user: null, loginId: '', loginPw: '' });
        }
      });
    } else {
      wx.removeStorageSync('token');
      wx.removeStorageSync('user_id');
      wx.removeStorageSync('club_id');
      this.setData({ loggedIn: false, user: null, loginId: '', loginPw: '' });
    }
  },
  openDetail(e) {
    const rec = this.data.records[e.currentTarget.dataset.index];
    wx.navigateTo({
      url:
        '/pages/recorddetail/recorddetail?data=' +
        encodeURIComponent(JSON.stringify(rec))
    });
  }
});
