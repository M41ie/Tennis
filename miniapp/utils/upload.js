// Upload avatar file and return the file URL.
// Usage:
//   uploadAvatar(path).then(url => { /* use url */ });
const BASE_URL = getApp().globalData.BASE_URL;

function uploadAvatar(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: `${BASE_URL}/upload`,
      filePath,
      name: 'file',
      success(res) {
        try {
          const data = JSON.parse(res.data);
          if (data && data.url) return resolve(data.url);
        } catch (e) {}
        reject(res);
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

module.exports = uploadAvatar;
