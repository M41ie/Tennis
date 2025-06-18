const request = require('../utils/request');

function getLeaderboard(params = {}) {
  const query = Object.entries(params)
    .filter(([_, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&');
  return request({ url: '/leaderboard_full' + (query ? '?' + query : '') });
}

function getClubInfo(id) {
  return request({ url: `/clubs/${id}` });
}

function getClubPlayers(id, opts = {}) {
  const suffix = opts.doubles ? '?doubles=true' : '';
  return request({ url: `/clubs/${id}/players${suffix}` });
}

function getAppointments(id) {
  return request({ url: `/clubs/${id}/appointments` });
}

function createAppointment(id, data) {
  return request({ url: `/clubs/${id}/appointments`, method: 'POST', data });
}

function signupAppointment(id, appointmentId, data) {
  return request({
    url: `/clubs/${id}/appointments/${appointmentId}/signup`,
    method: 'POST',
    data,
  });
}

function cancelAppointment(id, appointmentId, data) {
  return request({
    url: `/clubs/${id}/appointments/${appointmentId}/cancel`,
    method: 'POST',
    data,
  });
}

module.exports = {
  getLeaderboard,
  getClubInfo,
  getClubPlayers,
  getAppointments,
  createAppointment,
  signupAppointment,
  cancelAppointment,
};
