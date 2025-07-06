const { hideKeyboard } = require('../../utils/hideKeyboard');
const userService = require('../../services/user');
const store = require('../../store/store');
const { t } = require('../../utils/locales');
const ensureSubscribe = require('../../utils/ensureSubscribe');

Page({
  data: { t },
  hideKeyboard,
  async wechatLogin() {
    try {
      const res = await new Promise((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
      });
      if (!res.code) return;
      const resp = await userService.wechatLogin(res.code);
      if (resp.access_token) {
        store.setAuth(resp.access_token, resp.user_id, resp.refresh_token);
        await ensureSubscribe('club_join');
        await ensureSubscribe('match');
        wx.navigateBack();
      } else {
        wx.showToast({ duration: 4000, title: t.loginFailed, icon: 'none' });
      }
    } catch (e) {
      // ignore
    }
  }
});
