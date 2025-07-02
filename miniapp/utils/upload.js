// miniapp/utils/upload.js
const store = require('../store/store');

/**
 * 封装 wx.uploadFile, 用于上传文件并返回服务器提供的URL
 * @param {string} filePath - 要上传的文件的临时路径
 * @returns {Promise<string>} - 包含文件在服务器上可访问的相对URL的Promise
 */
function uploadAvatar(filePath) {
  // 在函数调用时才获取 BASE_URL，确保其已就绪
  const BASE_URL = getApp().globalData.BASE_URL;
  const token = store.token || wx.getStorageSync('token');

  // 返回一个 Promise，便于使用 async/await
  return new Promise((resolve, reject) => {
    console.log(`[upload.js] 准备上传到: ${BASE_URL}/upload/image`);

    wx.uploadFile({
      url: `${BASE_URL}/upload/image`,
      filePath,
      name: 'file',
      header: token ? { 'Authorization': `Bearer ${token}` } : {},
      success(res) {
        try {
          if (typeof res.data !== 'string') {
            return reject({ errMsg: '服务器响应格式错误', response: res });
          }
          const data = JSON.parse(res.data);

          if (res.statusCode >= 400) {
            const errorDetail = data.detail || '上传失败，请重试';
            wx.showToast({ duration: 4000, title: errorDetail, icon: 'none' });
            return reject(new Error(errorDetail));
          }

          if (data && data.url) {
            return resolve(data.url);
          }

          reject(new Error('服务器返回数据格式不正确'));
        } catch (e) {
          reject(new Error('响应数据解析失败'));
        }
      },
      fail(err) {
        reject(err);
      }
    });
  });
}

module.exports = uploadAvatar;
