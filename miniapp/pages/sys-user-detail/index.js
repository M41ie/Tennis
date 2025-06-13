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
    inputCreate: ''
  },
  onLoad(options) {
    if (options && options.user_id) {
      this.setData({ userId: options.user_id });
    }
    wx.setNavigationBarTitle({ title: '用户管理' });
    this.fetchDetail();
  },
  fetchDetail() {
    // TODO: load user detail and limits
  },
  openEdit() {
    this.setData({ showEdit: true, inputJoin: String(this.data.limits.max_joinable_clubs), inputCreate: String(this.data.limits.max_creatable_clubs) });
  },
  onJoinInput(e) { this.setData({ inputJoin: e.detail.value }); },
  onCreateInput(e) { this.setData({ inputCreate: e.detail.value }); },
  save() {
    // TODO: save limits via API
    this.setData({ showEdit: false });
  }
});
