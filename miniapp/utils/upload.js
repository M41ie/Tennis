// miniapp/utils/upload.js
const store = require('../store/store');

function uploadAvatar(filePath) {
  const BASE_URL = getApp().globalData.BASE_URL;
  const token = store.token || wx.getStorageSync('token');

  return new Promise((resolve, reject) => {
    // 【诊断】打印将要使用的Token，检查其是否存在
    console.log('[upload.js] 使用的Token:', token ? `Bearer ${token.substring(0, 30)}...` : '未找到Token');
    console.log(`[upload.js] 准备上传到: ${BASE_URL}/upload/image`);

    wx.uploadFile({
      url: `${BASE_URL}/upload/image`,
      filePath,
      name: 'file',
      header: token ? { 'Authorization': `Bearer ${token}` } : {},
      success(res) {
        // ======================= 新增的详细诊断日志 =======================
        console.log('[upload.js] wx.uploadFile success 回调, 服务器响应:', res);
        // =================================================================

        try {
          if (typeof res.data !== 'string') {
            // 【优化】更详细的错误对象
            return reject({ errMsg: '服务器响应格式错误，res.data非字符串', response: res });
          }
          const data = JSON.parse(res.data);

          if (res.statusCode >= 400) {
            const errorDetail = data.detail || '上传失败，请重试';
            wx.showToast({ duration: 4000, title: `上传错误: ${errorDetail}`, icon: 'none' }); // 【优化】显示更具体的错误
            // 【优化】将完整的服务器响应体和状态码都reject出去
            return reject({ errMsg: errorDetail, statusCode: res.statusCode, data: data });
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
        // ======================= 新增的详细诊断日志 =======================
        console.error('[upload.js] wx.uploadFile fail 回调, 错误详情:', err);
        // =================================================================
        reject(err);
      }
    });
  });
}

module.exports = uploadAvatar;
