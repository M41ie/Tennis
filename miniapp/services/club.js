const request = require('../utils/request');

function getLeaderboard(params = {}) {
  const query = Object.entries(params)
    .filter(([_, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  return request('/leaderboard_full' + (query ? '?' + query : ''));
}

module.exports = {
  getLeaderboard,
};
