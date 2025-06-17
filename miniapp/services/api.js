const request = require('../utils/request');

function api(options) {
  return request(options);
}

module.exports = api;
