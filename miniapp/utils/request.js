const BASE_URL = getApp().globalData.BASE_URL;

function request(path, options = {}) {
  const token = wx.getStorageSync('token');
  const opts = { ...options };
  opts.url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
  opts.method = opts.method || 'GET';
  opts.data = opts.data || {};
  opts.header = opts.header || {};
  if (token) {
    opts.header['Authorization'] = `Bearer ${token}`;
  }
  return new Promise((resolve, reject) => {
    wx.request({
      ...opts,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' });
          reject(res);
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' });
        reject(err);
      }
    });
  });
}

module.exports = request;
