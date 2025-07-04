const TEMPLATE_ID = 'uqaaIKXK918Yz4FGODyiuB4uJgMFkXC_63vTGq-0G2c_';

function ensureSubscribe(scene) {
  return new Promise(resolve => {
    wx.requestSubscribeMessage({
      tmplIds: [TEMPLATE_ID],
      success() { resolve(); },
      fail() { wx.showToast({ title: '请授权接收通知', icon: 'none' }); resolve(); }
    });
  });
}

module.exports = ensureSubscribe;
