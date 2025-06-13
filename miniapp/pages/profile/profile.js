const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');
const userService = require('../../services/user');

Page({
  data: {
    loggedIn: false,
    user: null,
    guestUser: {
      id: '-',
      name: '点击登陆/注册',
      rating_singles: '-',
      rating_doubles: '-',
      weighted_games_singles: '-',
      weighted_games_doubles: '-',
      avatar_url: ''
    },
    clubId: '',
    joinedClubs: [],
    isSysAdmin: false,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    iconClub: IMAGES.ICON_CLUB,
    iconComing: IMAGES.ICON_COMING,
    myClubBtnText: '我的俱乐部'
  },
  onShow() {
    const uid = wx.getStorageSync('user_id');
    const cid = wx.getStorageSync('club_id');
    if (uid) {
      this.setData({ loggedIn: true });
      this.loadJoinedClubs(uid, cid);
    } else {
      this.setData({ loggedIn: false, user: this.data.guestUser });
    }
  },
  loadJoinedClubs(uid, cid) {
    userService.getUserInfo(uid).then(res => {
      const list = res.joined_clubs || [];
      const isAdmin = !!res.sys_admin;
      let current = cid;
      if (!current && list.length) {
        current = list[0];
        wx.setStorageSync('club_id', current);
      }
      this.setData({
        joinedClubs: list,
        clubId: current || '',
        isSysAdmin: isAdmin
      });
      this.loadUser(uid);
    });
  },
  loadUser(uid) {
    userService.getPlayerInfo(uid).then(res => {
        const raw = res || {};
        const singlesCount = raw.weighted_games_singles ?? raw.weighted_singles_matches;
        const doublesCount = raw.weighted_games_doubles ?? raw.weighted_doubles_matches;
        const user = {
          id: raw.id || raw.user_id,
          avatar_url: raw.avatar_url || raw.avatar,
          name: raw.name,
          rating_singles: formatRating(raw.rating_singles ?? raw.singles_rating),
          rating_doubles: formatRating(raw.rating_doubles ?? raw.doubles_rating),
          weighted_games_singles: typeof singlesCount === 'number'
            ? singlesCount.toFixed(2)
            : (singlesCount ? Number(singlesCount).toFixed(2) : '--'),
          weighted_games_doubles: typeof doublesCount === 'number'
            ? doublesCount.toFixed(2)
            : (doublesCount ? Number(doublesCount).toFixed(2) : '--')
        };
        this.setData({ user });
    });
  },
  editProfile() {
    wx.navigateTo({ url: '/pages/editprofile/editprofile' });
  },
  toLogin() { wx.navigateTo({ url: '/pages/login/index' }); },
  toRegister() { wx.navigateTo({ url: '/pages/register/register' }); },
  onCardTap() {
    if (!this.data.loggedIn) {
      wx.navigateTo({ url: '/pages/login/index' });
    } else {
      wx.navigateTo({ url: '/pages/playercard/playercard' });
    }
  },
  goMyClub() {
    if (!this.data.loggedIn) return;
    wx.navigateTo({ url: '/pages/club-manage/index' });
  },
  goMyNotes() {
    wx.navigateTo({ url: '/pages/mynotes/mynotes' });
  },
  goSysManage() {
    if (!this.data.isSysAdmin) return;
    wx.navigateTo({ url: '/pages/sysmanage/sysmanage' });
  },
  logout() {
    const complete = () => {
      wx.removeStorageSync('token');
      wx.removeStorageSync('user_id');
      wx.removeStorageSync('club_id');
      this.setData({ loggedIn: false, user: this.data.guestUser });
    };
    userService.logout().finally(complete);
  }
});
