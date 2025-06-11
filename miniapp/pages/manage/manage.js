const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    pending: [],
    members: [],
    isAdmin: false,
    userId: '',
    clubName: '',
    clubSlogan: '',
    region: '',
    stats: {},
    role: '',
    roleText: ''
  },
  onLoad(options) {
    if (options && options.cid) {
      wx.setStorageSync('club_id', options.cid);
    }
    this.setData({ userId: wx.getStorageSync('user_id') });
    this.fetchClub();
    this.fetchPlayers();
  },
  fetchClub() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data;
        const isAdmin =
          info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId));
        let role = 'member';
        if (info.leader_id === that.data.userId) role = 'leader';
        else if (info.admin_ids && info.admin_ids.includes(that.data.userId))
          role = 'admin';
        const roleText = role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员';
        const stats = info.stats || {};
        const fmt = n =>
          typeof n === 'number' ? n.toFixed(1) : '--';
        if (Array.isArray(stats.singles_rating_range)) {
          stats.singles_rating_range = stats.singles_rating_range.map(fmt);
        }
        if (Array.isArray(stats.doubles_rating_range)) {
          stats.doubles_rating_range = stats.doubles_rating_range.map(fmt);
        }
        if (stats.singles_avg_rating != null) {
          stats.singles_avg_rating = fmt(stats.singles_avg_rating);
        }
        if (stats.doubles_avg_rating != null) {
          stats.doubles_avg_rating = fmt(stats.doubles_avg_rating);
        }
        if (stats.total_singles_matches != null) {
          stats.total_singles_matches = Math.round(stats.total_singles_matches);
        }
        if (stats.total_doubles_matches != null) {
          stats.total_doubles_matches = Math.round(stats.total_doubles_matches);
        }
        that.setData({
          pending: info.pending_members || [],
          isAdmin,
          clubName: info.name || '',
          clubSlogan: info.slogan || '',
          region: info.region || '',
          stats,
          role,
          roleText,
          leaderId: info.leader_id,
          adminIds: info.admin_ids || []
        });
      }
    });
  },
  fetchPlayers() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players`,
      success(res1) {
        const singles = res1.data || [];
        wx.request({
          url: `${BASE_URL}/clubs/${cid}/players?doubles=true`,
          success(res2) {
            const doubles = res2.data || [];
            const map = {};
            singles.forEach(p => {
              map[p.user_id] = {
                user_id: p.user_id,
                id: p.user_id,
                name: p.name,
                avatar: p.avatar,
                avatar_url: p.avatar,
                gender: p.gender,
                joined: p.joined,
                rating_singles: p.rating != null ? p.rating.toFixed(3) : '--',
                weighted_games_singles:
                  p.weighted_singles_matches != null
                    ? p.weighted_singles_matches.toFixed(2)
                    : '--'
              };
            });
            doubles.forEach(p => {
              const t = map[p.user_id] || {
                user_id: p.user_id,
                id: p.user_id,
                name: p.name,
                avatar: p.avatar,
                avatar_url: p.avatar,
                gender: p.gender,
                joined: p.joined
              };
              t.rating_doubles = p.rating != null ? p.rating.toFixed(3) : '--';
              t.weighted_games_doubles =
                p.weighted_doubles_matches != null
                  ? p.weighted_doubles_matches.toFixed(2)
                  : '--';
              map[p.user_id] = t;
            });
            const now = Date.now();
            const list = Object.values(map).map(p => {
              const joined = p.joined ? new Date(p.joined).getTime() : now;
              const days = Math.floor((now - joined) / (1000 * 60 * 60 * 24));
              const genderText =
                p.gender === 'M'
                  ? '男'
                  : p.gender === 'F'
                  ? '女'
                  : '-';
              p.infoLine = `${genderText} · 已加入俱乐部 ${days} 天`;
              const role =
                p.user_id === that.data.leaderId
                  ? 'leader'
                  : that.data.adminIds.includes(p.user_id)
                  ? 'admin'
                  : 'member';
              p.role = role;
              p.roleText = role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员';
              return p;
            });
            that.setData({ members: list });
          }
        });
      }
    });
  },
  approve(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/approve`,
      method: 'POST',
      data: { approver_id: this.data.userId, user_id: uid, token },
      complete() { that.fetchClub(); }
    });
  },
  kick(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/members/${uid}`,
      method: 'DELETE',
      data: { remover_id: this.data.userId, token, ban: false },
      complete() { that.fetchClub(); }
    });
  },
  ban(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/members/${uid}`,
      method: 'DELETE',
      data: { remover_id: this.data.userId, token, ban: true },
      complete() { that.fetchClub(); }
    });
  },
  viewPlayer(e) {
    const uid = e.currentTarget.dataset.uid;
    wx.navigateTo({ url: '/pages/playercard/playercard?uid=' + uid });
  },
  quitClub() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'quit' },
      complete() { wx.navigateBack(); }
    });
  },
  resignAdmin() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'resign_admin' },
      complete() { that.fetchClub(); }
    });
  },
  toggleAdmin() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'toggle_admin' },
      complete() { that.fetchClub(); }
    });
  },
  transferLeader() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'transfer_leader' },
      complete() { that.fetchClub(); }
    });
  }
});
