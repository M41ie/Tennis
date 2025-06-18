const request = require('../utils/request');

function getPlayerRecords(userId, { doubles = false, limit = 10, offset = 0 } = {}) {
  const path = doubles ? 'doubles_records' : 'records';
  const query = `?limit=${limit}&offset=${offset}`;
  return request({ url: `/players/${userId}/${path}${query}` });
}

function getPlayerPendingSingles(userId, token) {
  return request({ url: `/players/${userId}/pending_matches`, data: { token } });
}

function getPlayerPendingDoubles(userId, token) {
  return request({ url: `/players/${userId}/pending_doubles`, data: { token } });
}

function confirmSingleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_matches/${matchId}/confirm`,
    method: 'POST',
    data,
  });
}

function approveSingleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_matches/${matchId}/approve`,
    method: 'POST',
    data,
  });
}

function vetoSingleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_matches/${matchId}/veto`,
    method: 'POST',
    data,
  });
}

function rejectSingleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_matches/${matchId}/reject`,
    method: 'POST',
    data,
  });
}

function confirmDoubleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_doubles/${matchId}/confirm`,
    method: 'POST',
    data,
  });
}

function approveDoubleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_doubles/${matchId}/approve`,
    method: 'POST',
    data,
  });
}

function vetoDoubleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_doubles/${matchId}/veto`,
    method: 'POST',
    data,
  });
}

function rejectDoubleMatch(clubId, matchId, data) {
  return request({
    url: `/clubs/${clubId}/pending_doubles/${matchId}/reject`,
    method: 'POST',
    data,
  });
}

module.exports = {
  getPlayerRecords,
  getPlayerPendingSingles,
  getPlayerPendingDoubles,
  confirmSingleMatch,
  approveSingleMatch,
  vetoSingleMatch,
  rejectSingleMatch,
  confirmDoubleMatch,
  approveDoubleMatch,
  vetoDoubleMatch,
  rejectDoubleMatch,
};
