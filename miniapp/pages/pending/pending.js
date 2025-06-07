const BASE_URL = getApp().globalData.BASE_URL;

Page({
  data: {
    tabIndex: 0,
    singles: [],
    doubles: [],
    userId: '',
    isAdmin: false,
    matchToShare: null
  },
  onLoad() {
    this.setData({ userId: wx.getStorageSync('user_id') });
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
        const list = res.data.map(it => {
          const item = {};
          item.index = it.index;
          item.score_a = it.score_a;
          item.score_b = it.score_b;
          item.player_a_name = it.player_a_name;
          item.rating_a_before = it.rating_a_before ? it.rating_a_before.toFixed(3) : 'N/A';
          item.player_b_name = it.player_b_name;
          item.rating_b_before = it.rating_b_before ? it.rating_b_before.toFixed(3) : 'N/A';
          item.statusText = it.display_status_text || '';
          item.showConfirmButton = it.can_confirm;
          item.showDeclineButton = it.can_decline;
          item.showApproveButton = that.data.isAdmin && it.can_approve;
          item.showVetoButton = that.data.isAdmin && it.can_veto;
          item.originalData = it; // Pass original data for share context
          return item;
        });
        that.setData({ singles: list });
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
        const list = res.data.map(it => {
          const item = {};
          item.index = it.index;
          item.score_a = it.score_a;
          item.score_b = it.score_b;
          item.a1_name = it.a1_name;
          item.rating_a1_before = it.rating_a1_before ? it.rating_a1_before.toFixed(3) : 'N/A';
          item.a2_name = it.a2_name;
          item.rating_a2_before = it.rating_a2_before ? it.rating_a2_before.toFixed(3) : 'N/A';
          item.b1_name = it.b1_name;
          item.rating_b1_before = it.rating_b1_before ? it.rating_b1_before.toFixed(3) : 'N/A';
          item.b2_name = it.b2_name;
          item.rating_b2_before = it.rating_b2_before ? it.rating_b2_before.toFixed(3) : 'N/A';
          item.statusText = it.display_status_text || '';
          item.showConfirmButton = it.can_confirm;
          item.showDeclineButton = it.can_decline;
          item.showApproveButton = that.data.isAdmin && it.can_approve;
          item.showVetoButton = that.data.isAdmin && it.can_veto;
          item.originalData = it; // Pass original data for share context
          return item;
        });
        that.setData({ doubles: list });
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
  onShareAppMessage(options) {
    const defaultShareMsg = {
      title: '待确认战绩',
      path: '/pages/pending/pending',
      imageUrl: '' // Optional: add a generic image URL
    };
    let shareMsg = { ...defaultShareMsg };

    if (options.from === 'button' && this.data.matchToShare) {
      const match = this.data.matchToShare;
      let matchTitle = '待确认比赛';
      // let matchType = ''; // Not strictly needed for title, but could be for path

      if (match.player_a_name) { // Singles match
        matchTitle = `${match.player_a_name} (${match.rating_a_before || 'N/A'}) vs ${match.player_b_name} (${match.rating_b_before || 'N/A'})`;
        // matchType = 'singles';
      } else if (match.a1_name) { // Doubles match
        matchTitle = `${match.a1_name}(${match.rating_a1_before || 'N/A'})/${match.a2_name}(${match.rating_a2_before || 'N/A'}) vs ${match.b1_name}(${match.rating_b1_before || 'N/A'})/${match.b2_name}(${match.rating_b2_before || 'N/A'})`;
        // matchType = 'doubles';
      }

      shareMsg.title = `待确认: ${match.score_a}-${match.score_b} ${matchTitle}`;
      // Path can be used to highlight the specific match upon opening the app via share card
      // For simplicity, we'll just point to the pending page. Highlighting can be a future enhancement.
      // shareMsg.path = `/pages/pending/pending?matchIndex=${match.index}&type=${matchType}&clubId=${wx.getStorageSync('club_id')}`;
      // console.log('Sharing specific match:', shareMsg);
      this.setData({ matchToShare: null }); // Clear after use
    }
    return shareMsg;
  },
  vetoDouble(e) {
    console.log("vetoDouble clicked for item index:", e.currentTarget.dataset.index);
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
  shareMatch(e) {
    const matchInfo = e.currentTarget.dataset.matchInfo;
    if (matchInfo) {
      this.setData({ matchToShare: matchInfo });
      // Programmatically trigger the share behavior
      // wx.shareAppMessage is not directly callable here to trigger menu.
      // Instead, rely on onShareAppMessage being configured correctly
      // and wx.showShareMenu to just show the option if needed.
      // The button click itself is the trigger for onShareAppMessage if it comes from a button.
      console.log('Match data set for sharing:', matchInfo);
      wx.showShareMenu({ // This ensures the native share menu appears if not triggered by open-type button
        withShareTicket: true,
        menus: ['shareAppMessage', 'shareTimeline']
      });
    } else {
      console.error('No matchInfo found for sharing');
    }
  },
});
