const BASE_URL = getApp().globalData.BASE_URL;
const request = require('../../utils/request');
const { hideKeyboard } = require('../../utils/hideKeyboard');
const { formatRating, formatGames, withBase } = require('../../utils/format');
const { formatClubCardData } = require('../../utils/clubFormat');
const store = require('../../store/store');
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
    userId: '',
    user: null,
    limits: {
      max_joinable_clubs: 5,
      max_creatable_clubs: 0
    },
    showEdit: false,
    inputJoin: '',
    inputCreate: '',
    records: [],
    recPage: 1,
    recFinished: false,
    modeIndex: 0,
    doubles: false,
    showRating: false,
    ratingSingles: '',
    ratingDoubles: ''
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
          avatar_url: withBase(d.avatar_url || d.avatar),
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
    this.setData({ recPage: 1, recFinished: false, records: [] });
    this.fetchRecords();
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
  },
  switchMode(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ modeIndex: idx, doubles: idx == 1, recPage: 1, recFinished: false, records: [] });
    this.fetchRecords();
  },
  fetchRecords() {
    const uid = this.data.userId;
    if (!uid) return;
    const placeholder = require('../../assets/base64.js').DEFAULT_AVATAR;
    const that = this;
    const limit = 10;
    const offset = (this.data.recPage - 1) * limit;
    const path = this.data.doubles ? 'doubles_records' : 'records';
    request({
      url: `${BASE_URL}/players/${uid}/${path}?limit=${limit}&offset=${offset}`,
      success(res) {
        const list = res.data || [];
        const user = that.data.user || {};
        list.forEach(rec => {
          rec.scoreA = rec.self_score;
          rec.scoreB = rec.opponent_score;
          rec.playerAName = user.name || '';
          rec.playerAAvatar = user.avatar_url || placeholder;
          rec.ratingA = rec.self_rating_after != null ? Number(rec.self_rating_after).toFixed(3) : '';
          const d = rec.self_delta;
          if (d != null) {
            const delta = Number(d);
            const abs = Math.abs(delta).toFixed(3);
            rec.deltaDisplayA = (delta > 0 ? '+' : delta < 0 ? '-' : '') + abs;
            rec.deltaClassA = delta > 0 ? 'pos' : delta < 0 ? 'neg' : 'neutral';
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
            }
          }
          rec.displayFormat = displayFormat(rec.format);
        });
        if (that.data.recPage === 1) {
          that.setData({ records: list, recFinished: list.length < limit });
        } else {
          const start = that.data.records.length;
          const obj = { recFinished: list.length < limit };
          list.forEach((item, i) => {
            obj[`records[${start + i}]`] = item;
          });
          that.setData(obj);
        }
      }
    });
  },
  openRating() {
    const u = this.data.user || {};
    this.setData({ showRating: true, ratingSingles: u.singles_rating || '', ratingDoubles: u.doubles_rating || '' });
  },
  closeRating() { this.setData({ showRating: false }); },
  onSinglesInput(e) { this.setData({ ratingSingles: e.detail.value }); },
  onDoublesInput(e) { this.setData({ ratingDoubles: e.detail.value }); },
  saveRating() {
    const uid = this.data.userId;
    const s = parseFloat(this.data.ratingSingles);
    const d = parseFloat(this.data.ratingDoubles);
    const that = this;
    request({
      url: `${BASE_URL}/sys/users/${uid}/rating`,
      method: 'POST',
      data: { singles_rating: isNaN(s) ? undefined : s, doubles_rating: isNaN(d) ? undefined : d },
      success(res) {
        if (res.statusCode === 200) {
          wx.showToast({ duration: 4000, title: '已更新' });
          that.fetchDetail();
        } else {
          wx.showToast({ duration: 4000, title: '失败', icon: 'none' });
        }
      },
      complete() { that.setData({ showRating: false }); }
    });
  },
  onReachBottom() {
    if (this.data.recFinished) return;
    this.setData({ recPage: this.data.recPage + 1 });
    this.fetchRecords();
  },
  onPullDownRefresh() {
    this.setData({ recPage: 1, recFinished: false, records: [] });
    this.fetchRecords();
    wx.stopPullDownRefresh();
  }
});
