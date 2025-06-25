const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { formatRating, formatGames } = require('../../utils/format');
const { formatClubCardData } = require('../../utils/clubFormat');
const store = require('../../store/store');

Page({
  data: {
    userId: '',
    user: null,
    limits: {
      max_joinable_clubs: 5,
      max_creatable_clubs: 0
    },
    showEdit: false,
    inputJoin: '',
    inputCreate: ''
  },
  onLoad(options) {
    if (options && options.user_id) {
      this.setData({ userId: options.user_id });
    }
    wx.setNavigationBarTitle({ title: '用户管理' });
    this.fetchDetail();
  },
  fetchDetail() {
    const uid = this.data.userId;
    if (!uid) return;
    const that = this;
    request({
      url: `${BASE_URL}/players/${uid}`,
      success(res) {
        const d = res.data || {};
        const user = {
          id: d.id || uid,
          name: d.name,
          avatar_url: d.avatar_url || d.avatar,
          singles_rating: formatRating(d.singles_rating),
          doubles_rating: formatRating(d.doubles_rating),
          weighted_games_singles: formatGames(d.weighted_games_singles),
          weighted_games_doubles: formatGames(d.weighted_games_doubles),
          clubs: []
        };
        that.setData({ user });
      }
    });
    request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        const info = res.data || {};
        const ids = info.joined_clubs || [];
        const limits = {
          max_joinable_clubs: info.max_joinable_clubs != null ? info.max_joinable_clubs : 5,
          max_creatable_clubs: info.max_creatable_clubs != null ? info.max_creatable_clubs : 0
        };
        that.setData({ limits });
        if (!ids.length) return;
        const list = [];
        let count = 0;
        ids.forEach(cid => {
          request({
            url: `${BASE_URL}/clubs/${cid}`,
            success(r) {
              const info = r.data || {};
              const card = formatClubCardData(info, uid);
              card.club_id = cid;
              list.push(card);
            },
            complete() {
              count++;
              if (count === ids.length) {
                const user = that.data.user || {};
                user.clubs = list;
                that.setData({ user });
              }
            }
          });
        });
      }
    });
  },
  openEdit() {
    this.setData({ showEdit: true, inputJoin: String(this.data.limits.max_joinable_clubs), inputCreate: String(this.data.limits.max_creatable_clubs) });
  },
  close() { this.setData({ showEdit: false }); },
  hideKeyboard,
  noop() {},
  onJoinInput(e) { this.setData({ inputJoin: e.detail.value }); },
  onCreateInput(e) { this.setData({ inputCreate: e.detail.value }); },
  save() {
    const uid = this.data.userId;
    const join = Number(this.data.inputJoin);
    const create = Number(this.data.inputCreate);
    const token = store.token;
    const that = this;
    wx.showModal({
      title: '确认修改',
      content: '确认要修改该用户的权限吗？',
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/sys/users/${uid}/limits`,
            method: 'POST',
            data: { max_joinable_clubs: join, max_creatable_clubs: create, token },
            success(res) {
              if (res.statusCode === 200) {
                wx.showToast({ duration: 4000,  title: '修改成功' });
                that.setData({
                  'limits.max_joinable_clubs': join,
                  'limits.max_creatable_clubs': create
                });
                that.fetchDetail();
              } else {
                const msg = (res.data && res.data.detail) || '修改失败';
                wx.showToast({ duration: 4000,  title: msg, icon: 'none' });
              }
            },
            complete() {
              that.setData({ showEdit: false });
            }
          });
        }
      }
    });
  }
});
