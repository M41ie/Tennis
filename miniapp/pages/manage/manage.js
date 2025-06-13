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
  loadPendingNames(list) {
    const that = this;
    if (!list.length) {
      this.setData({ pending: [] });
      return;
    }
    const result = [];
    let count = 0;
    list.forEach(p => {
      wx.request({
        url: `${BASE_URL}/players/${p.user_id}`,
        success(r) {
          if (r.statusCode !== 200) {
            wx.request({
              url: `${BASE_URL}/users/${p.user_id}`,
              success(u) {
                const name = u.data && u.data.name ? u.data.name : p.user_id;
                result.push({
                  ...p,
                  id: p.user_id,
                  name,
                  avatar_url: '',
                  gender: '',
                  genderText: '-',
                  rating_singles:
                    p.singles_rating != null ? p.singles_rating.toFixed(3) : '--',
                  rating_doubles:
                    p.doubles_rating != null ? p.doubles_rating.toFixed(3) : '--',
                  weighted_games_singles: '--',
                  weighted_games_doubles: '--',
                  global_rating: null
                });
              },
              complete() {
                count++;
                if (count === list.length) that.setData({ pending: result });
              }
            });
            return;
          }
          const d = r.data || {};
          const rating =
            typeof d.singles_rating === 'number' ? d.singles_rating : null;
          const doublesRating =
            typeof d.doubles_rating === 'number' ? d.doubles_rating : null;
          const gender = d.gender || '';
          const genderText =
            gender === 'M' || gender === 'Male' || gender === '男'
              ? '男'
              : gender === 'F' || gender === 'Female' || gender === '女'
              ? '女'
              : '-';
          result.push({
            ...p,
            id: p.user_id,
            name: d.name || p.user_id,
            avatar_url: d.avatar_url || d.avatar || '',
            gender,
            genderText,
            rating_singles: rating != null ? rating.toFixed(3) : '--',
            rating_doubles: doublesRating != null ? doublesRating.toFixed(3) : '--',
            weighted_games_singles:
              d.weighted_games_singles != null
                ? Number(d.weighted_games_singles).toFixed(2)
                : '--',
            weighted_games_doubles:
              d.weighted_games_doubles != null
                ? Number(d.weighted_games_doubles).toFixed(2)
                : '--',
            global_rating: rating
          });
          count++;
          if (count === list.length) {
            that.setData({ pending: result });
          }
        },
        fail() {
          wx.request({
            url: `${BASE_URL}/users/${p.user_id}`,
            success(r) {
              const name = r.data && r.data.name ? r.data.name : p.user_id;
              result.push({
                ...p,
                id: p.user_id,
                name,
                avatar_url: '',
                gender: '',
                genderText: '-',
                rating_singles:
                  p.singles_rating != null ? p.singles_rating.toFixed(3) : '--',
                rating_doubles:
                  p.doubles_rating != null ? p.doubles_rating.toFixed(3) : '--',
                weighted_games_singles: '--',
                weighted_games_doubles: '--',
                global_rating: null
              });
            },
            complete() {
              count++;
              if (count === list.length) that.setData({ pending: result });
            }
          });
        }
      });
    });
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
        that.loadPendingNames(info.pending_members || []);
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
                ratingSinglesNum: typeof p.rating === 'number' ? p.rating : null,
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
              t.ratingDoublesNum =
                typeof p.rating === 'number' ? p.rating : null;
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
              p.genderText = genderText;
              p.daysText = `已加入${days}天`;
              p.days = days;
              const role =
                p.user_id === that.data.leaderId
                  ? 'leader'
                  : that.data.adminIds.includes(p.user_id)
                  ? 'admin'
                  : 'member';
              p.role = role;
              p.roleText =
                role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员';
              p.genderRoleText = `${genderText} · ${p.roleText}`;
              const rs =
                typeof p.ratingSinglesNum === 'number' ? p.ratingSinglesNum : 0;
              const rd =
                typeof p.ratingDoublesNum === 'number' ? p.ratingDoublesNum : 0;
              p.totalRating = rs + rd;
              return p;
            });
            list.sort((a, b) => {
              if (b.days !== a.days) return b.days - a.days;
              return b.totalRating - a.totalRating;
            });
            that.setData({ members: list });
          }
        });
      }
    });
  },
  approveById(uid, rating) {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/approve`,
      method: 'POST',
      data: { approver_id: this.data.userId, user_id: uid, rating, token },
      complete() { that.fetchClub(); }
    });
  },
  handleApproval(uid) {
    const applicant = this.data.pending.find(p => p.user_id === uid);
    if (!applicant) return;
    if (typeof applicant.global_rating === 'number') {
      this.approveById(uid, applicant.global_rating);
      return;
    }
    const that = this;
    wx.showModal({
      title: '设置初始评分',
      editable: true,
      placeholderText: '如3.5',
      success(res) {
        if (res.confirm) {
          const rating = parseFloat(res.content);
          if (isNaN(rating)) {
            wx.showToast({ title: '无效评分', icon: 'none' });
            return;
          }
          that.approveById(uid, rating);
        }
      }
    });
  },
  approve(e) {
    this.handleApproval(e.currentTarget.dataset.uid);
  },
  rejectById(uid, reason) {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/reject`,
      method: 'POST',
      data: { approver_id: this.data.userId, user_id: uid, reason, token },
      complete() { that.fetchClub(); }
    });
  },
  reviewApplication(e) {
    const uid = e.currentTarget.dataset.uid;
    const applicant = this.data.pending.find(p => p.user_id === uid);
    if (!applicant) return;
    const lines = [];
    if (applicant.reason) lines.push('理由：' + applicant.reason);
    if (applicant.singles_rating != null)
      lines.push('单打自评：' + applicant.singles_rating);
    if (applicant.doubles_rating != null)
      lines.push('双打自评：' + applicant.doubles_rating);
    const that = this;
    wx.showModal({
      title: applicant.name || applicant.user_id,
      content: lines.join('\n'),
      confirmText: '通过',
      cancelText: '拒绝',
      success(res) {
        if (res.confirm) {
          that.handleApproval(uid);
        } else if (res.cancel) {
          wx.showModal({
            title: '拒绝理由',
            editable: true,
            placeholderText: '请输入理由',
            success(r) {
              if (r.confirm) {
                const reason = r.content || '';
                that.rejectById(uid, reason);
              }
            }
          });
        }
      }
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
    wx.navigateTo({ url: '/pages/membercard/membercard?uid=' + uid });
  },
  quitClub() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.showModal({
      title: '确认退出',
      content: `确认要退出${that.data.clubName}吗？`,
      confirmColor: '#e03a3a',
      success(res) {
        if (res.confirm) {
          wx.request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
            data: { user_id: uid, token, action: 'quit' },
            complete() { wx.navigateBack(); }
          });
        }
      }
    });
  },
  resignAdmin() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const uid = this.data.userId;
    const that = this;
    wx.showModal({
      title: '确认卸任',
      content: `确认要卸任${that.data.clubName}的管理员吗？`,
      confirmColor: '#e03a3a',
      success(res) {
        if (res.confirm) {
          wx.request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
            data: { user_id: uid, token, action: 'resign_admin' },
            complete() { that.fetchClub(); }
          });
        }
      }
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
  },
  editClub() {
    wx.navigateTo({ url: '/pages/editclub/editclub' });
  }
});
