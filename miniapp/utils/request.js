const BASE_URL = getApp().globalData.BASE_URL;
const store = require('../store/store');
const { zh_CN: t } = require('./locales');

function request(options = {}, _retry = true) {
  const token = store.token;
  const refreshToken = store.refreshToken;
  const opts = { ...options };
  const url = opts.url || '';
  opts.url = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  opts.method = opts.method || 'GET';
  opts.data = opts.data || {};
  opts.header = opts.header || {};
  opts.header['Authorization'] = token ? `Bearer ${token}` : '';
  const showLoading = opts.loading !== false;
  if (showLoading) wx.showLoading({ title: t.loading, mask: true });
  return new Promise((resolve, reject) => {
    wx.request({
      ...opts,
      success(res) {
        if (res.statusCode === 401 && refreshToken && _retry) {
          wx.request({
            url: `${BASE_URL}/refresh_token`,
            method: 'POST',
            data: { refresh_token: refreshToken },
            success(r) {
              if (r.statusCode === 200 && r.data.access_token) {
                store.setAuth(r.data.access_token, store.userId, refreshToken);
                opts.header['Authorization'] = `Bearer ${r.data.access_token}`;
                request(options, false).then(resolve, reject);
              } else {
                store.clearAuth();
                wx.navigateTo({ url: '/pages/login/index' });
                wx.showToast({ duration: 4000,  title: t.pleaseRelogin, icon: 'none' });
                opts.fail && opts.fail(res);
                reject(res);
              }
            },
            fail(err) {
              store.clearAuth();
              wx.navigateTo({ url: '/pages/login/index' });
              wx.showToast({ duration: 4000,  title: t.pleaseRelogin, icon: 'none' });
              opts.fail && opts.fail(err);
              reject(err);
            }
          });
          return;
        }
        if (res.statusCode === 401) {
          store.clearAuth();
          wx.navigateTo({ url: '/pages/login/index' });
          wx.showToast({ duration: 4000,  title: t.pleaseRelogin, icon: 'none' });
          opts.fail && opts.fail(res);
          reject(res);
          return;
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          opts.success && opts.success(res);
          resolve(res.data);
        } else {
          wx.showToast({ duration: 4000,  title: res.data.detail || t.requestFailed, icon: 'none' });
          opts.fail && opts.fail(res);
          reject(res);
        }
      },
      fail(err) {
        wx.showToast({ duration: 4000,  title: t.networkError, icon: 'none' });
        opts.fail && opts.fail(err);
        reject(err);
      },
      complete(res) {
        if (showLoading) wx.hideLoading();
        opts.complete && opts.complete(res);
      }
    });
  });
}

module.exports = request;
