const request = require('../utils/request');

function wechatLogin(code) {
  return request({ url: '/wechat_login', method: 'POST', data: { code } });
}

function logout() {
  return request({ url: '/logout', method: 'POST' });
}

function getUserInfo(userId) {
  return request({ url: `/users/${userId}` });
}

function getPlayerInfo(userId) {
  return request({ url: `/players/${userId}` });
}

module.exports = {
  wechatLogin,
  logout,
  getUserInfo,
  getPlayerInfo,
};
