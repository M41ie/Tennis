const request = require('../utils/request');

function wechatLogin(code) {
  return request('/wechat_login', { method: 'POST', data: { code } });
}

function logout() {
  return request('/logout', { method: 'POST' });
}

function getUserInfo(userId) {
  return request(`/users/${userId}`);
}

function getPlayerInfo(userId) {
  return request(`/players/${userId}`);
}

module.exports = {
  wechatLogin,
  logout,
  getUserInfo,
  getPlayerInfo,
};
