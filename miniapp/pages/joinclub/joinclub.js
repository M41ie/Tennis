const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    clubs: [],
    query: '',
    joined: [],
    showDialog: false,
    joinClubId: '',
    needRating: false,
    rating: '',
    reason: ''
  },
  onLoad(options) {
    if (options && options.query) {
      this.setData({ query: options.query });
    }
    this.fetchJoined();
  },
  fetchJoined() {
    const uid = wx.getStorageSync('user_id');
    const that = this;
    if (!uid) {
      this.setData({ joined: [] });
      this.fetchClubs();
      return;
    }
    wx.request({
      url: `${BASE_URL}/users/${uid}`,
      success(res) {
        that.setData({ joined: res.data.joined_clubs || [] });
      },
      complete() {
        that.fetchClubs();
      }
    });
  },
  fetchClubs() {
    const that = this;
    const uid = wx.getStorageSync('user_id');
    wx.request({
      url: `${BASE_URL}/clubs`,
      success(res) {
        let list = res.data;
        const q = that.data.query;
        if (q) {
          list = list.filter(c => c.name.includes(q) || c.club_id.includes(q));
        }
        if (!list.length) {
          that.setData({ clubs: [] });
          return;
        }
        const result = [];
        let count = 0;
        list.forEach(c => {
          wx.request({
            url: `${BASE_URL}/clubs/${c.club_id}`,
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
              const pending = (info.pending_members || []).some(
                m => m.user_id === uid
              );
              const rejected = info.rejected_members
                ? info.rejected_members[uid]
                : '';
              result.push({
                club_id: c.club_id,
                name: c.name,
                slogan: info.slogan || '',
                region: info.region || '',
                member_count: stats.member_count,
                singles_range: sr.length ? `${fmt(sr[0])}-${fmt(sr[1])}` : '--',
                doubles_range: dr.length ? `${fmt(dr[0])}-${fmt(dr[1])}` : '--',
                total_singles:
                  stats.total_singles_matches != null
                    ? stats.total_singles_matches.toFixed(0)
                    : '--',
                total_doubles:
                  stats.total_doubles_matches != null
                    ? stats.total_doubles_matches.toFixed(0)
                    : '--',
                singles_avg: singlesAvg,
                doubles_avg: doublesAvg,
                joined: that.data.joined.includes(c.club_id),
                pending,
                rejected_reason: rejected
              });
            },
            complete() {
              count++;
              if (count === list.length) {
                that.setData({ clubs: result });
              }
            }
          });
        });
      }
    });
  },
  join(e) {
    const cid = e.currentTarget.dataset.id;
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    if (!userId || !token) return;
    wx.request({
      url: `${BASE_URL}/users/${userId}`,
      success(res) {
        const limit =
          res.data.max_joinable_clubs != null ? res.data.max_joinable_clubs : 5;
        if (res.data.joined_clubs && res.data.joined_clubs.length >= limit) {
          wx.showToast({ title: '加入俱乐部的数量已达上限', icon: 'none' });
          return;
        }
        wx.request({
          url: `${BASE_URL}/players/${userId}`,
          success(pres) {
            const info = pres.data || {};
            const need =
              info.singles_rating == null && info.doubles_rating == null;
              that.setData({
                showDialog: true,
                joinClubId: cid,
                needRating: need,
                rating: '',
                reason: ''
              });
          }
        });
      }
    });
  },
  onRating(e) {
    this.setData({ rating: e.detail.value });
  },
  onReason(e) {
    this.setData({ reason: e.detail.value });
  },
  cancelJoin() {
    this.setData({ showDialog: false });
  },
  noop() {},
  viewReject(e) {
    const reason = e.currentTarget.dataset.reason;
    const cid = e.currentTarget.dataset.id;
    const uid = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.showModal({
      title: '未通过原因',
      content: reason || '',
      showCancel: false,
      confirmText: '了解',
      success() {
        wx.request({
          url: `${BASE_URL}/clubs/${cid}/clear_rejection`,
          method: 'POST',
          data: { user_id: uid, token },
          complete() {
            that.fetchJoined();
          }
        });
      }
    });
  },
  submitJoin() {
    const userId = wx.getStorageSync('user_id');
    const token = wx.getStorageSync('token');
    const cid = this.data.joinClubId;
    const rating = parseFloat(this.data.rating);
    if (
      (this.data.needRating && (isNaN(rating) || rating < 0 || rating > 7)) ||
      !this.data.reason
    ) {
      wx.showToast({ title: '请完善信息', icon: 'none' });
      return;
    }
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/join`,
      method: 'POST',
        data: {
          user_id: userId,
          token,
          singles_rating: this.data.needRating ? rating : undefined,
          doubles_rating: this.data.needRating ? rating : undefined,
          reason: this.data.reason
        },
      success(r) {
        if (r.statusCode === 200) {
          wx.setStorageSync('club_id', cid);
          wx.showToast({ title: '已申请', icon: 'success' });
          const clubs = that.data.clubs.map(c =>
            c.club_id === cid ? { ...c, pending: true, rejected_reason: '' } : c
          );
          that.setData({ clubs, showDialog: false });
        } else {
          wx.showToast({ title: '失败', icon: 'none' });
        }
      }
    });
  }
});
