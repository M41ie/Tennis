const TEMPLATE_ID = 'uqaaIKXK918Yz4FGODyiuB4uJgMFkXC_63vTGq-0G2c';
const BASE_URL = getApp().globalData.BASE_URL;
const store = require('../store/store');
const request = require('./request');

function ensureSubscribe(scene) {
  return new Promise(resolve => {
    wx.requestSubscribeMessage({
      tmplIds: [TEMPLATE_ID],
      success() {
        request({
          url: `${BASE_URL}/subscribe`,
          method: 'POST',
          data: { user_id: store.userId, token: store.token, scene }
        }).finally(() => resolve());
      },
      fail() { resolve(); }
    });
  });
}

module.exports = ensureSubscribe;
