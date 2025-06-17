const IMAGES = require('../../assets/base64.js');
const { formatRating } = require('../../utils/format');
const userService = require('../../services/user');
const store = require('../../store/store');

Page({
  data: {
    loggedIn: false,
    user: null,
    guestUser: {
      id: '-',
      name: '点击登陆/注册',
      singles_rating: '-',
      doubles_rating: '-',
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
    const uid = store.userId;
    const cid = store.clubId;
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
        store.setClubId(current);
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
          singles_rating: formatRating(raw.singles_rating),
          doubles_rating: formatRating(raw.doubles_rating),
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
      wx.login({
        success: res => {
          if (!res.code) return;
          userService
            .wechatLogin(res.code)
            .then(resp => {
              if (resp.token) {
                store.setAuth(resp.token, resp.user_id);
                this.setData({ loggedIn: true });
                if (resp.just_created) {
                  wx.navigateTo({ url: '/pages/editprofile/editprofile' });
                } else {
                  this.loadJoinedClubs(
                    resp.user_id,
                    store.clubId
                  );
                }
              } else {
                wx.showToast({ title: '登录失败', icon: 'none' });
              }
            })
            .catch(() => {});
        }
      });
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
      store.clearAuth();
      this.setData({ loggedIn: false, user: this.data.guestUser });
    };
    userService.logout().finally(complete);
  }
});
