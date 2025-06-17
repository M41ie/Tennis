const BASE_URL = getApp().globalData.BASE_URL;

function request(options = {}) {
  const token = wx.getStorageSync('token');
  const opts = { ...options };
  const url = opts.url || '';
  opts.url = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  opts.method = opts.method || 'GET';
  opts.data = opts.data || {};
  opts.header = opts.header || {};
  if (token) {
    opts.header['Authorization'] = `Bearer ${token}`;
  }
  wx.showLoading({ title: '加载中', mask: true });
  return new Promise((resolve, reject) => {
    wx.request({
      ...opts,
      success(res) {
        if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('user_id');
          wx.removeStorageSync('club_id');
          wx.navigateTo({ url: '/pages/login/index' });
          wx.showToast({ title: '请重新登录', icon: 'none' });
          opts.fail && opts.fail(res);
          reject(res);
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          opts.success && opts.success(res);
          resolve(res.data);
        } else {
          wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' });
          opts.fail && opts.fail(res);
          reject(res);
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' });
        opts.fail && opts.fail(err);
        reject(err);
      },
      complete(res) {
        wx.hideLoading();
        opts.complete && opts.complete(res);
      }
    });
  });
}

module.exports = request;
