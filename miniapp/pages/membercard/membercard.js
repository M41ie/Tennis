const BASE_URL = getApp().globalData.BASE_URL;
const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');

function calcAge(birth) {
  const d = new Date(birth);
  if (isNaN(d)) return '';
  const diff = Date.now() - d.getTime();
  return Math.floor(diff / (365 * 24 * 60 * 60 * 1000));
}

function genderText(g) {
  if (!g) return '';
  if (g === 'M' || g === 'Male' || g === '男') return '男';
  if (g === 'F' || g === 'Female' || g === '女') return '女';
  return g;
}

function formatExtraLines(info) {
  const line1 = [];
  const gender = genderText(info.gender);
  if (gender) line1.push(gender);
  const age = calcAge(info.birth);
  if (age) line1.push(`${age}岁`);

  const line2 = [];
  if (info.handedness) line2.push(info.handedness);
  if (info.backhand) line2.push(info.backhand);

  return { line1: line1.join('·'), line2: line2.join('·') };
}

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
    isSelf: false
  },
  onLoad(options) {
    const memberId = options && options.uid ? options.uid : '';
    const selfId = wx.getStorageSync('user_id');
    this.setData({ memberId, isSelf: memberId === selfId });
  },
  onShow() {
    this.loadUser();
    this.loadClubInfo();
  },
  loadUser() {
    const cid = wx.getStorageSync('club_id');
    if (!cid || !this.data.memberId) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/players/${this.data.memberId}`,
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
          rating_singles: formatRating(raw.rating_singles ?? raw.singles_rating),
          rating_doubles: formatRating(raw.rating_doubles ?? raw.doubles_rating),
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
    const cid = wx.getStorageSync('club_id');
    const uid = wx.getStorageSync('user_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data || {};
        let role = 'member';
        if (info.leader_id === uid) role = 'leader';
        else if (info.admin_ids && info.admin_ids.includes(uid)) role = 'admin';
        const targetAdmin = info.admin_ids && info.admin_ids.includes(that.data.memberId);
        const targetLeader = info.leader_id === that.data.memberId;
        const isSelf = that.data.memberId === uid;
        that.setData({
          myRole: role,
          isTargetAdmin: !!targetAdmin,
          isTargetLeader: !!targetLeader,
          isSelf
        });
      }
    });
  },
  toggleAdmin() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const action = this.data.isTargetAdmin ? '取消管理员' : '设为管理员';
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '确认操作',
      content: `确认将${name}${action}？`,
      success(res) {
        if (res.confirm) {
          wx.request({
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
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '转移负责人',
      content: `确认将负责人转移给${name}？`,
      success(res) {
        if (res.confirm) {
          wx.request({
            url: `${BASE_URL}/clubs/${cid}/role`,
            method: 'POST',
            data: { user_id: that.data.memberId, token, action: 'transfer_leader' },
            complete() { that.loadClubInfo(); }
          });
        }
      }
    });
  },
  removeMember() {
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const remover = wx.getStorageSync('user_id');
    const name = this.data.user ? this.data.user.name : '';
    const that = this;
    wx.showModal({
      title: '移除成员',
      content: `确认将${name}从俱乐部移除？`,
      success(res) {
        if (res.confirm) {
          wx.request({
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
