const request = require('../utils/request');

function login(userId, password) {
  return request('/login', { method: 'POST', data: { user_id: userId, password } });
}

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
  login,
  wechatLogin,
  logout,
  getUserInfo,
  getPlayerInfo,
};
