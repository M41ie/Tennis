const { zh_CN: t } = require('./locales');

function showError(msg) {
  wx.showToast({ duration: 4000,  title: msg, icon: 'none' });
}

function validateClubName(name) {
  const ok = /^[A-Za-z\u4e00-\u9fa5]{1,20}$/.test(name);
  if (!ok) showError(t.clubNameRule);
  return ok;
}

function validateUserName(name) {
  const ok = /^[A-Za-z\u4e00-\u9fa5]{1,12}$/.test(name);
  if (!ok) showError(t.nameRule);
  return ok;
}

function validateRating(val) {
  const rating = parseFloat(val);
  const ok = !isNaN(rating) && rating >= 0 && rating <= 7;
  if (!ok) {
    showError(t.ratingFormatError);
    return null;
  }
  return rating;
}

module.exports = {
  showError,
  validateClubName,
  validateUserName,
  validateRating
};
