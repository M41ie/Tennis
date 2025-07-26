const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const userService = require('../../services/user');
const store = require('../../store/store');
const IMAGES = require('../../assets/base64.js');
const { formatRating, withBase } = require('../../utils/format');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { formatExtraLines } = require('../../utils/userFormat');
const { t } = require('../../utils/locales');

const FORMAT_DISPLAY = {
  '6_game': '六局',
  '4_game': '四局',
  tb10: '抢十',
  tb7: '抢七',
  '6局': '六局',
  '4局': '四局',
  '抢10': '抢十',
  '抢7': '抢七'
};

function displayFormat(fmt) {
  return FORMAT_DISPLAY[fmt] || fmt;
}

Page({
  data: {
    t,
    friendId: '',
    user: null,
    placeholderAvatar: IMAGES.DEFAULT_AVATAR,
    infoLine1: '',
    infoLine2: '',
    modeIndex: 0,
    doubles: false,
    records: [],
    page: 1,
    finished: false,
    isLoading: true,
    isError: false,
    isEmpty: false
  },
  hideKeyboard,
  onLoad(options) {
    const fid = options && options.uid ? options.uid : '';
    this.setData({ friendId: fid });
  },
  onShow() {
    this.loadUser();
    this.setData({ page: 1, records: [], finished: false, isLoading: true, isError: false, isEmpty: false });
    this.fetchRecords();
  },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx, doubles: idx == 1, page: 1, records: [], finished: false, isLoading: true, isError: false, isEmpty: false });
    this.fetchRecords();
  },
  loadUser() {
    const fid = this.data.friendId;
    if (!fid) return;
    const that = this;
    userService.getPlayerInfo(fid).then(raw => {
      const singlesCount = raw.weighted_games_singles ?? raw.weighted_singles_matches;
      const doublesCount = raw.weighted_games_doubles ?? raw.weighted_doubles_matches;
      const user = {
        id: raw.id || raw.user_id,
        avatar_url: withBase(raw.avatar_url || raw.avatar),
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
      const line1 = extra.line1.replace(/(?:^|·)\d+岁/, '');
      that.setData({
        user,
        infoLine1: line1,
        infoLine2: extra.line2
      });
    });
  },
  fetchRecords() {
    const userId = store.userId;
    const friendId = this.data.friendId;
    if (!userId || !friendId) return;
    const that = this;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    const limit = 10;
    const offset = (this.data.page - 1) * limit;
    this.setData({ isLoading: this.data.page === 1, isError: false, isEmpty: false });
    request({
      url: `${BASE_URL}/players/${userId}`,
      loading: false,
      success(res) {
        const player = res.data || {};
        const path = that.data.doubles ? 'doubles_records' : 'records';
        request({
          url: `${BASE_URL}/players/${userId}/${path}?limit=${limit}&offset=${offset}`,
          loading: false,
          success(r) {
            let list = r.data || [];
            list = list.filter(rec => {
              if (!that.data.doubles) {
                return rec.opponent_id === friendId;
              }
              return rec.partner_id === friendId || rec.opponent1_id === friendId || rec.opponent2_id === friendId;
            });
            list.forEach(rec => {
              rec.scoreA = rec.self_score;
              rec.scoreB = rec.opponent_score;
              rec.playerAName = player.name || '';
              rec.playerAAvatar = withBase(player.avatar_url || player.avatar) || placeholder;
              rec.ratingA = rec.self_rating_after != null ? Number(rec.self_rating_after).toFixed(3) : '';
              const d = rec.self_delta;
              if (d != null) {
                const delta = Number(d);
                const abs = Math.abs(delta).toFixed(3);
                rec.deltaDisplayA = (delta > 0 ? '+' : delta < 0 ? '-' : '') + abs;
                rec.deltaClassA = delta > 0 ? 'pos' : delta < 0 ? 'neg' : 'neutral';
              } else {
                rec.deltaDisplayA = '';
                rec.deltaClassA = 'neutral';
              }

              if (!that.data.doubles) {
                rec.playerBName = rec.opponent || '';
                rec.playerBAvatar = withBase(rec.opponent_avatar) || placeholder;
                rec.ratingB = rec.opponent_rating_after != null ? Number(rec.opponent_rating_after).toFixed(3) : '';
                const d2 = rec.opponent_delta;
                if (d2 != null) {
                  const delta2 = Number(d2);
                  const abs2 = Math.abs(delta2).toFixed(3);
                  rec.deltaDisplayB = (delta2 > 0 ? '+' : delta2 < 0 ? '-' : '') + abs2;
                  rec.deltaClassB = delta2 > 0 ? 'pos' : delta2 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.deltaDisplayB = '';
                  rec.deltaClassB = 'neutral';
                }
              } else {
                rec.partnerName = rec.partner || '';
                rec.partnerAvatar = withBase(rec.partner_avatar) || placeholder;
                rec.partnerRating = rec.partner_rating_after != null ? Number(rec.partner_rating_after).toFixed(3) : '';
                const pd = rec.partner_delta;
                if (pd != null) {
                  const deltaP = Number(pd);
                  const abs = Math.abs(deltaP).toFixed(3);
                  rec.partnerDeltaDisplay = (deltaP > 0 ? '+' : deltaP < 0 ? '-' : '') + abs;
                  rec.partnerDeltaClass = deltaP > 0 ? 'pos' : deltaP < 0 ? 'neg' : 'neutral';
                } else {
                  rec.partnerDeltaDisplay = '';
                  rec.partnerDeltaClass = 'neutral';
                }

                rec.opp1Name = rec.opponent1 || '';
                rec.opp1Avatar = withBase(rec.opponent1_avatar) || placeholder;
                rec.opp1Rating = rec.opponent1_rating_after != null ? Number(rec.opponent1_rating_after).toFixed(3) : '';
                const od1 = rec.opponent1_delta;
                if (od1 != null) {
                  const delta1 = Number(od1);
                  const abs = Math.abs(delta1).toFixed(3);
                  rec.opp1DeltaDisplay = (delta1 > 0 ? '+' : delta1 < 0 ? '-' : '') + abs;
                  rec.opp1DeltaClass = delta1 > 0 ? 'pos' : delta1 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.opp1DeltaDisplay = '';
                  rec.opp1DeltaClass = 'neutral';
                }

                rec.opp2Name = rec.opponent2 || '';
                rec.opp2Avatar = withBase(rec.opponent2_avatar) || placeholder;
                rec.opp2Rating = rec.opponent2_rating_after != null ? Number(rec.opponent2_rating_after).toFixed(3) : '';
                const od2 = rec.opponent2_delta;
                if (od2 != null) {
                  const delta2 = Number(od2);
                  const abs = Math.abs(delta2).toFixed(3);
                  rec.opp2DeltaDisplay = (delta2 > 0 ? '+' : delta2 < 0 ? '-' : '') + abs;
                  rec.opp2DeltaClass = delta2 > 0 ? 'pos' : delta2 < 0 ? 'neg' : 'neutral';
                } else {
                  rec.opp2DeltaDisplay = '';
                  rec.opp2DeltaClass = 'neutral';
                }
              }

              rec.displayFormat = displayFormat(rec.format);
            });
            if (that.data.page === 1) {
              that.setData({
                records: list,
                finished: list.length < limit,
                isLoading: false,
                isEmpty: list.length === 0
              });
            } else {
              const start = that.data.records.length;
              const obj = { finished: list.length < limit, isLoading: false };
              list.forEach((item, i) => {
                obj[`records[${start + i}]`] = item;
              });
              that.setData(obj);
            }
          },
          fail() {
            that.setData({ isLoading: false, isError: true });
          }
        });
      },
      fail() {
        that.setData({ isLoading: false, isError: true });
      }
    });
  },
  viewRecord(e) {
    const rec = this.data.records[e.currentTarget.dataset.index];
    wx.navigateTo({
      url: '/pages/recorddetail/recorddetail?data=' + encodeURIComponent(JSON.stringify(rec))
    });
  },
  onPullDownRefresh() {
    this.setData({ page: 1, records: [], finished: false, isLoading: true, isError: false, isEmpty: false });
    this.fetchRecords();
    wx.stopPullDownRefresh();
  },
  onReachBottom() {
    if (this.data.finished) return;
    this.setData({ page: this.data.page + 1 });
    this.fetchRecords();
  }
});
