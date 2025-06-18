const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');
const store = require('../../store/store');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { formatExtraLines } = require('../../utils/userFormat');

Page({
  data: {
    user: null,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    infoLine1: '',
    infoLine2: '',
    memberId: '',
    myRole: '',
    isTargetAdmin: false,
    isTargetLeader: false,
    isSelf: false,
    isSysAdmin: false,
    clubName: ''
  },
  hideKeyboard,
  onLoad(options) {
    const memberId = options && options.uid ? options.uid : '';
    const selfId = store.userId;
    this.setData({ memberId, isSelf: memberId === selfId });
  },
  onShow() {
    this.loadUser();
    this.checkSysAdmin();
  },
  checkSysAdmin() {
    const uid = store.userId;
    const that = this;
    if (!uid) {
      that.setData({ isSysAdmin: false });
      that.loadClubInfo();
      return;
    }
    request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        that.setData({ isSysAdmin: !!res.data.sys_admin });
      },
      complete() {
        that.loadClubInfo();
      }
    });
  },
  loadUser() {
    if (!this.data.memberId) return;
    const that = this;
    request({
      url: `${BASE_URL}/players/${this.data.memberId}`,
      success(res) {
        const raw = res.data || {};
        const singlesCount = raw.weighted_games_singles ?? raw.weighted_singles_matches;
        const doublesCount = raw.weighted_games_doubles ?? raw.weighted_doubles_matches;
        const user = {
          id: raw.id || raw.user_id,
          avatar_url: raw.avatar_url || raw.avatar,
          name: raw.name,
          gender: raw.gender,
          birth: raw.birth,
          handedness: raw.handedness,
          backhand: raw.backhand,
          singles_rating: formatRating(raw.singles_rating),
          doubles_rating: formatRating(raw.doubles_rating),
          weighted_games_singles: typeof singlesCount === 'number'
            ? singlesCount.toFixed(2)
            : (singlesCount ? Number(singlesCount).toFixed(2) : '--'),
          weighted_games_doubles: typeof doublesCount === 'number'
            ? doublesCount.toFixed(2)
            : (doublesCount ? Number(doublesCount).toFixed(2) : '--')
        };
        const extra = formatExtraLines(user);
        that.setData({
          user,
          infoLine1: extra.line1,
          infoLine2: extra.line2
        });
      }
    });
  },
  loadClubInfo() {
    const cid = store.clubId;
    const uid = store.userId;
    if (!cid) return;
    const that = this;
    request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data || {};
        let role = 'member';
        if (info.leader_id === uid) role = 'leader';
        else if (info.admin_ids && info.admin_ids.includes(uid)) role = 'admin';
        if (that.data.isSysAdmin) role = 'leader';
        const targetAdmin = info.admin_ids && info.admin_ids.includes(that.data.memberId);
        const targetLeader = info.leader_id === that.data.memberId;
        const isSelf = that.data.memberId === uid;
        that.setData({
          clubName: info.name || '',
          myRole: role,
          isTargetAdmin: !!targetAdmin,
          isTargetLeader: !!targetLeader,
          isSelf
        });
      }
    });
  },
  toggleAdmin() {
    const cid = store.clubId;
    const token = store.token;
    const action = this.data.isTargetAdmin ? '取消管理员' : '设为管理员';
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '确认操作',
      content: `确认将${name}${action}？`,
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
            data: { user_id: that.data.memberId, token, action: 'toggle_admin' },
            complete() { that.loadClubInfo(); }
          });
        }
      }
    });
  },
  transferLeader() {
    const cid = store.clubId;
    const token = store.token;
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '转移负责人',
      content: `确认将负责人转移给${name}？`,
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
          data: { user_id: that.data.memberId, token, action: 'transfer_leader' },
          complete() { that.loadClubInfo(); }
        });
      }
    }
  });
  },
  setLeader() {
    if (!this.data.isSysAdmin) return;
    const cid = store.clubId;
    const token = store.token;
    const uid = this.data.memberId;
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '设为负责人',
      content: `确定要将 ${name} 设为 ${that.data.clubName} 的负责人吗？此操作不可逆`,
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/sys/clubs/${cid}/leader`,
            method: 'POST',
            data: { user_id: uid, token },
            success() {
              wx.showToast({ title: '操作成功', icon: 'none' });
            },
            complete() { that.loadClubInfo(); }
          });
        }
      }
    });
  },
  removeMember() {
    const cid = store.clubId;
    const token = store.token;
    const remover = store.userId;
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '移除成员',
      content: `确认将${name}从俱乐部移除？`,
      success(res) {
        if (res.confirm) {
          request({
            url: `${BASE_URL}/clubs/${cid}/members/${that.data.memberId}`,
            method: 'DELETE',
            data: { remover_id: remover, token, ban: false },
            complete() { wx.navigateBack(); }
          });
        }
      }
    });
  }
});
