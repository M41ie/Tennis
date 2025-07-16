const request = require('../utils/request');

function getFriends(userId) {
  return request({ url: `/players/${userId}/friends` });
}

module.exports = {
  getFriends,
};
