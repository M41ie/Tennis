let env = 'develop';

if (typeof wx !== 'undefined' && wx.getAccountInfoSync) {
  try {
    env = wx.getAccountInfoSync().miniProgram.envVersion;
  } catch (e) {}
} else if (process && process.env && process.env.MINIAPP_ENV) {
  env = process.env.MINIAPP_ENV;
}

const CONFIG = {
  develop: { BASE_URL: 'http://119.45.169.39:8002' },
  trial:   { BASE_URL: 'https://api.tennisrating.top:8001' },
  release: { BASE_URL: 'https://api.tennisrating.top:8000' }
};

module.exports = CONFIG[env] || CONFIG.develop;
