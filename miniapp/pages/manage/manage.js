const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { zh_CN } = require('../../utils/locales.js');
const { genderText } = require('../../utils/userFormat');
const store = require('../../store/store');
const { withBase } = require('../../utils/format');
const ensureSubscribe = require('../../utils/ensureSubscribe');

Page({
  data: {
    t: zh_CN,
    pending: [],
    members: [],
    isAdmin: false,
    isSysAdmin: false,
    userId: '',
    clubName: '',
    clubSlogan: '',
    region: '',
    stats: {},
    role: '',
    roleText: '',
    showRatingDialog: false,
    ratingInput: '',
    ratingDialogTitle: '',
    ratingApplicantId: '',
    joinStatus: 'joined'
  },
  onLoad(options) {
    if (options && options.cid) {
      store.setClubId(options.cid);
    }
    this.setData({ userId: store.userId });
    this.checkSysAdmin();
  },
  onShow() {
    this.fetchPlayers();
  },
  checkSysAdmin() {
    const uid = this.data.userId;
    const that = this;
    if (!uid) {
      that.fetchClub();
      that.fetchPlayers();
      return;
    }
    request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        that.setData({ isSysAdmin: !!res.data.sys_admin });
      },
      complete() {
        that.fetchClub();
        that.fetchPlayers();
      }
    });
  },
  loadPendingNames() {
    const cid = store.clubId;
    if (!cid) {
      this.setData({ pending: [] });
      return;
    }
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/pending_members`,
      success(res) {
        const list = res.data || [];
        const result = list.map(p => {
          const gender = p.gender || '';
          const gText = genderText(gender) || '-';
          return {
            ...p,
            singles_rating:
              p.singles_rating != null ? Number(p.singles_rating).toFixed(3) : '--',
            doubles_rating:
              p.doubles_rating != null ? Number(p.doubles_rating).toFixed(3) : '--',
            weighted_games_singles:
              p.weighted_games_singles != null
                ? Number(p.weighted_games_singles).toFixed(2)
                : '--',
            weighted_games_doubles:
              p.weighted_games_doubles != null
                ? Number(p.weighted_games_doubles).toFixed(2)
                : '--',
            gender,
            genderText: gText,
            id: p.user_id
          };
        });
        that.setData({ pending: result });
      }
    });
  },
  fetchClub() {
    const cid = store.clubId;
    if (!cid) return;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data;
        const members = info.members || [];
        const pendingList = info.pending_members || [];
        const rejectedMap = info.rejected_members || {};
        const isMember =
          info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId)) ||
          members.some(m => m.user_id === that.data.userId);
        const isAdmin =
          info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId)) ||
          that.data.isSysAdmin;
        let role = '';
        if (isMember) {
          role = 'member';
          if (info.leader_id === that.data.userId) role = 'leader';
          else if (info.admin_ids && info.admin_ids.includes(that.data.userId)) role = 'admin';
        }
        const roleText =
          role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : role ? '成员' : '';
        const pending = pendingList.some(p => p.user_id === that.data.userId);
        const rejected = rejectedMap[that.data.userId] || '';
        const joinStatus = isMember ? 'joined' : pending ? 'pending' : rejected ? 'rejected' : 'apply';
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
          adminIds: info.admin_ids || [],
          joinStatus
        });
        that.loadPendingNames();
      }
    });
  },
  fetchPlayers() {
    const cid = store.clubId;
    if (!cid) return;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/players`,
      success(res1) {
        const singles = res1.data || [];
        request({
          url: `${BASE_URL}/clubs/${cid}/players?doubles=true`,
          success(res2) {
            const doubles = res2.data || [];
            const map = {};
            singles.forEach(p => {
              map[p.user_id] = {
                user_id: p.user_id,
                id: p.user_id,
                name: p.name,
                avatar: withBase(p.avatar),
                avatar_url: withBase(p.avatar),
                gender: p.gender,
                joined: p.joined,
                singles_rating: p.singles_rating != null ? p.singles_rating.toFixed(3) : '--',
                ratingSinglesNum: typeof p.singles_rating === 'number' ? p.singles_rating : null,
                matchSinglesNum: typeof p.weighted_singles_matches === 'number' ? p.weighted_singles_matches : 0,
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
                avatar: withBase(p.avatar),
                avatar_url: withBase(p.avatar),
                gender: p.gender,
                joined: p.joined
              };
              t.doubles_rating = p.doubles_rating != null ? p.doubles_rating.toFixed(3) : '--';
              t.ratingDoublesNum =
                typeof p.doubles_rating === 'number' ? p.doubles_rating : null;
              t.matchDoublesNum =
                typeof p.weighted_doubles_matches === 'number'
                  ? p.weighted_doubles_matches
                  : 0;
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
              const gText = genderText(p.gender) || '-';
              p.genderText = gText;
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
              p.genderRoleText = `${gText} · ${p.roleText}`;
              const rs =
                typeof p.ratingSinglesNum === 'number' ? p.ratingSinglesNum : 0;
              const rd =
                typeof p.ratingDoublesNum === 'number' ? p.ratingDoublesNum : 0;
              p.totalRating = rs + rd;
              const ms =
                typeof p.matchSinglesNum === 'number' ? p.matchSinglesNum : 0;
              const md =
                typeof p.matchDoublesNum === 'number' ? p.matchDoublesNum : 0;
              p.totalMatches = ms + md;
              return p;
            });
            list.sort((a, b) => {
              const roleScore = { leader: 2, admin: 1, member: 0 };
              if (roleScore[b.role] !== roleScore[a.role])
                return roleScore[b.role] - roleScore[a.role];
              if (b.days !== a.days) return b.days - a.days;
              if (b.totalRating !== a.totalRating)
                return b.totalRating - a.totalRating;
              return b.totalMatches - a.totalMatches;
            });
            that.setData({ members: list });
          }
        });
      }
    });
  },
  approveById(uid, rating) {
    const cid = store.clubId;
    const token = store.token;
    const that = this;
    ensureSubscribe('club_manage');
    request({
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
    const title =
      uid === this.data.userId
        ? '请为自己评定初始评分'
        : `请为${applicant.name || applicant.user_id}评定初始评分`;
    this.setData({
      showRatingDialog: true,
      ratingInput: '',
      ratingDialogTitle: title,
      ratingApplicantId: uid
    });
  },
  onRatingInput(e) {
    this.setData({ ratingInput: e.detail.value });
  },
  cancelRating() {
    this.setData({ showRatingDialog: false });
  },
  confirmRating() {
    const rating = parseFloat(this.data.ratingInput);
    if (isNaN(rating)) {
      wx.showToast({ duration: 4000,  title: '无效评分', icon: 'none' });
      return;
    }
    const uid = this.data.ratingApplicantId;
    this.setData({ showRatingDialog: false, ratingInput: '', ratingApplicantId: '' });
    this.approveById(uid, rating);
  },
  hideKeyboard,
  noop() {},
  approve(e) {
    this.handleApproval(e.currentTarget.dataset.uid);
  },
  rejectById(uid, reason) {
    const cid = store.clubId;
    const token = store.token;
    const that = this;
    ensureSubscribe('club_manage');
    request({
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
    if (applicant.singles_rating != null) {
      const label =
        applicant.global_rating != null ? '单打评分：' : '单打自评：';
      lines.push(label + applicant.singles_rating);
    }
    if (applicant.doubles_rating != null) {
      const label =
        applicant.global_rating != null ? '双打评分：' : '双打自评：';
      lines.push(label + applicant.doubles_rating);
    }
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
    const cid = store.clubId;
    const token = store.token;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/members/${uid}`,
      method: 'DELETE',
      data: { remover_id: this.data.userId, token, ban: false },
      complete() { that.fetchClub(); }
    });
  },
  ban(e) {
    const uid = e.currentTarget.dataset.uid;
    const cid = store.clubId;
    const token = store.token;
    const that = this;
    request({
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
    const cid = store.clubId;
    const token = store.token;
    const uid = this.data.userId;
    const that = this;
    wx.showModal({
      title: this.data.t.confirmQuit,
      content: `确认要退出${that.data.clubName}吗？`,
      confirmColor: '#e03a3a',
      success(res) {
        if (res.confirm) {
          request({
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
    const cid = store.clubId;
    const token = store.token;
    const uid = this.data.userId;
    const that = this;
    wx.showModal({
      title: this.data.t.confirmResign,
      content: `确认要卸任${that.data.clubName}的管理员吗？`,
      confirmColor: '#e03a3a',
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
            data: { user_id: uid, token, action: 'resign_admin' },
            complete() { that.fetchClub(); }
          });
        }
      }
    });
  },
  transferLeader() {
    const cid = store.clubId;
    const token = store.token;
    const uid = this.data.userId;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}/role`,
      method: 'POST',
      data: { user_id: uid, token, action: 'transfer_leader' },
      complete() { that.fetchClub(); }
    });
  },
  dissolveClub() {
    const cid = store.clubId;
    const token = store.token;
    const uid = this.data.userId;
    const that = this;
    wx.showModal({
      title: this.data.t.confirmDissolve,
      content: `确认解散${that.data.clubName}吗？`,
      confirmColor: '#e03a3a',
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/clubs/${cid}`,
            method: 'DELETE',
            data: { user_id: uid, token },
            success() { wx.navigateBack(); }
          });
        }
      }
    });
  },
  applyJoin() {
    const cid = store.clubId;
    wx.navigateTo({ url: `/pkg_club/joinclub/joinclub?cid=${cid}` });
  },
  onShareAppMessage() {
    const cid = store.clubId;
    return {
      title: `${this.data.clubName} 俱乐部`,
      path: `/pages/manage/manage?cid=${cid}`
    };
  },
  editClub() {
    wx.navigateTo({ url: '/pkg_club/editclub/editclub' });
  }
});
