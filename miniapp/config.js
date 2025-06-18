let env = 'develop';

if (typeof wx !== 'undefined' && wx.getAccountInfoSync) {
  try {
    env = wx.getAccountInfoSync().miniProgram.envVersion;
  } catch (e) {}
} else if (process && process.env && process.env.MINIAPP_ENV) {
  env = process.env.MINIAPP_ENV;
}

const CONFIG = {
  develop: { BASE_URL: 'http://localhost:8000' },
  trial:   { BASE_URL: 'http://119.45.169.39' },
  release: { BASE_URL: 'https://api.example.com' }
};

module.exports = CONFIG[env] || CONFIG.develop;
