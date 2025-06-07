const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    tabIndex: 0,
    singles: [],
    doubles: [],
    userId: '',
    isAdmin: false,
    highlightIndex: null,
    highlightType: ''
  },
  onLoad(options) {
    this.setData({ userId: wx.getStorageSync('user_id') });
    if (options && options.tab) {
      const tab = parseInt(options.tab, 10);
      if (!Number.isNaN(tab)) {
        this.setData({ tabIndex: tab });
      }
    }
    if (options && options.index) {
      const idx = parseInt(options.index, 10);
      if (!Number.isNaN(idx)) {
        this.setData({ highlightIndex: idx });
      }
    }
    if (options && options.type) {
      this.setData({ highlightType: options.type });
    }
    this.fetchClubInfo();
  },
  switchTab(e) {
    const idx = e.currentTarget.dataset.index;
    this.setData({ tabIndex: idx });
  },
  fetchClubInfo() {
    const cid = wx.getStorageSync('club_id');
    if (!cid) return;
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}`,
      success(res) {
        const info = res.data;
        const admin = info.leader_id === that.data.userId ||
          (info.admin_ids && info.admin_ids.includes(that.data.userId));
        that.setData({ isAdmin: admin });
      },
      complete() { that.fetchPendings(); }
    });
  },
  fetchPendings() {
    const cid = wx.getStorageSync('club_id');
    const that = this;
    if (!cid) return;
    const token = wx.getStorageSync('token');
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches`,
      data: { token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '加载失败', icon: 'none' });
          return;
        }
        const isAdmin = that.data.isAdmin;
        const highlight =
          that.data.highlightType === 'single' ? that.data.highlightIndex : null;
        const list = res.data.map((it, i) => {
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.status = it.display_status_text || '';
          it.canApprove = isAdmin && it.confirmed_a && it.confirmed_b;
          it.canVeto = isAdmin && it.confirmed_a && it.confirmed_b;
          it.highlight = highlight === i;
          return it;
        });
        that.setData({ singles: list });
        if (highlight !== null) {
          setTimeout(() => that.scrollToHighlight(), 50);
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles`,
      data: { token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '加载失败', icon: 'none' });
          return;
        }
        const isAdmin = that.data.isAdmin;
        const highlight =
          that.data.highlightType === 'double' ? that.data.highlightIndex : null;
        const list = res.data.map((it, i) => {
          it.canConfirm = it.can_confirm;
          it.canReject = it.can_decline;
          it.status = it.display_status_text || '';
          it.canApprove = isAdmin && it.confirmed_a && it.confirmed_b;
          it.canVeto = isAdmin && it.confirmed_a && it.confirmed_b;
          it.highlight = highlight === i;
          return it;
        });
        that.setData({ doubles: list });
        if (highlight !== null) {
          setTimeout(() => that.scrollToHighlight(), 50);
        }
      },
      fail() {
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
  },
  confirmSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/confirm`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: '网络错误', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  },
  approveSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/approve`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: '网络错误', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  },
  vetoSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/veto`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      complete() { that.fetchPendings(); }
    });
  },
  rejectSingle(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_matches/${idx}/reject`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: '网络错误', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  },
  confirmDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/confirm`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: '网络错误', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  },
  approveDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/approve`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: '网络错误', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  },
  vetoDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/veto`,
      method: 'POST',
      data: { approver: this.data.userId, token },
      complete() { that.fetchPendings(); }
    });
  },
  rejectDouble(e) {
    const idx = e.currentTarget.dataset.index;
    const cid = wx.getStorageSync('club_id');
    const token = wx.getStorageSync('token');
    const that = this;
    wx.request({
      url: `${BASE_URL}/clubs/${cid}/pending_doubles/${idx}/reject`,
      method: 'POST',
      data: { user_id: this.data.userId, token },
      success(res) {
        if (res.statusCode >= 300) {
          wx.showToast({ title: '错误', icon: 'none' });
        }
      },
      fail() { wx.showToast({ title: '网络错误', icon: 'none' }); },
      complete() { that.fetchPendings(); }
    });
  },
  scrollToHighlight() {
    const idx = this.data.highlightIndex;
    const type = this.data.highlightType;
    if (idx === null || !type) return;
    const id = type === 'double' ? `double-${idx}` : `single-${idx}`;
    wx.createSelectorQuery()
      .select(`#${id}`)
      .boundingClientRect(rect => {
        if (rect) {
          wx.pageScrollTo({ scrollTop: rect.top - 80, duration: 0 });
        }
      })
      .exec();
  },
  onShareAppMessage(options) {
    if (options.from === 'button') {
      const { index, type } = options.target.dataset;
      const tab = type === 'double' ? 1 : 0;
      return {
        title: '待确认战绩',
        path: `/pages/pending/pending?tab=${tab}&index=${index}&type=${type}`,
      };
    }
    return { title: '待确认战绩', path: '/pages/pending/pending' };
  }
});
