const BASE_URL = getApp().globalData.BASE_URL;
const { formatRating, formatGames } = require('../../utils/format');

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
    wx.request({
      url: `${BASE_URL}/players/${uid}`,
      success(res) {
        const d = res.data || {};
        const user = {
          id: d.id || uid,
          name: d.name,
          avatar_url: d.avatar_url || d.avatar,
          rating_singles: formatRating(d.rating_singles),
          rating_doubles: formatRating(d.rating_doubles),
          weighted_games_singles: formatGames(d.weighted_games_singles),
          weighted_games_doubles: formatGames(d.weighted_games_doubles),
          clubs: []
        };
        that.setData({ user });
      }
    });
    wx.request({
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
          wx.request({
            url: `${BASE_URL}/clubs/${cid}`,
            success(r) {
              const info = r.data || {};
              const stats = info.stats || {};
              const sr = stats.singles_rating_range || [];
              const dr = stats.doubles_rating_range || [];
              const fmt = n => (typeof n === 'number' ? n.toFixed(1) : '--');
              const singlesAvg =
                typeof stats.singles_avg_rating === 'number'
                  ? fmt(stats.singles_avg_rating)
                  : '--';
              const doublesAvg =
                typeof stats.doubles_avg_rating === 'number'
                  ? fmt(stats.doubles_avg_rating)
                  : '--';
              let role = 'member';
              if (info.leader_id === uid) role = 'leader';
              else if (info.admin_ids && info.admin_ids.includes(uid)) role = 'admin';
              list.push({
                club_id: cid,
                name: info.name,
                slogan: info.slogan || '',
                region: info.region || '',
                role,
                roleText: role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员',
                member_count: stats.member_count,
                singles_range: sr.length ? `${fmt(sr[0])}-${fmt(sr[1])}` : '--',
                doubles_range: dr.length ? `${fmt(dr[0])}-${fmt(dr[1])}` : '--',
                total_singles: stats.total_singles_matches != null ?
                  stats.total_singles_matches.toFixed(0) : '--',
                total_doubles: stats.total_doubles_matches != null ?
                  stats.total_doubles_matches.toFixed(0) : '--',
                singles_avg: singlesAvg,
                doubles_avg: doublesAvg
              });
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
  hideKeyboard() {
    wx.hideKeyboard();
  },
  noop() {},
  onJoinInput(e) { this.setData({ inputJoin: e.detail.value }); },
  onCreateInput(e) { this.setData({ inputCreate: e.detail.value }); },
  save() {
    const uid = this.data.userId;
    const join = Number(this.data.inputJoin);
    const create = Number(this.data.inputCreate);
    const token = wx.getStorageSync('token');
    const that = this;
    wx.showModal({
      title: '确认修改',
      content: '确认要修改该用户的权限吗？',
      success(res) {
        if (res.confirm) {
          wx.request({
            url: `${BASE_URL}/sys/users/${uid}/limits`,
            method: 'POST',
            data: { max_joinable_clubs: join, max_creatable_clubs: create, token },
            success(res) {
              if (res.statusCode === 200) {
                wx.showToast({ title: '修改成功' });
                that.setData({
                  'limits.max_joinable_clubs': join,
                  'limits.max_creatable_clubs': create
                });
                that.fetchDetail();
              } else {
                const msg = (res.data && res.data.detail) || '修改失败';
                wx.showToast({ title: msg, icon: 'none' });
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
