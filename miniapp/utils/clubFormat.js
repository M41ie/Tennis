function formatClubStats(info) {
  const stats = info.stats || {};
  const sr = stats.singles_rating_range || [];
  const dr = stats.doubles_rating_range || [];
  const fmt = n => (typeof n === 'number' ? n.toFixed(1) : '--');
  return {
    member_count: stats.member_count,
    singles_range: sr.length ? `${fmt(sr[0])}-${fmt(sr[1])}` : '--',
    doubles_range: dr.length ? `${fmt(dr[0])}-${fmt(dr[1])}` : '--',
    total_singles:
      stats.total_singles_matches != null
        ? stats.total_singles_matches.toFixed(0)
        : '--',
    total_doubles:
      stats.total_doubles_matches != null
        ? stats.total_doubles_matches.toFixed(0)
        : '--',
    singles_avg:
      typeof stats.singles_avg_rating === 'number'
        ? fmt(stats.singles_avg_rating)
        : '--',
    doubles_avg:
      typeof stats.doubles_avg_rating === 'number'
        ? fmt(stats.doubles_avg_rating)
        : '--'
  };
}

function formatClubCardData(info, uid) {
  const base = {
    club_id: info.club_id,
    name: info.name,
    slogan: info.slogan || '',
    region: info.region || ''
  };
  Object.assign(base, formatClubStats(info));
  if (uid) {
    let role = 'member';
    if (info.leader_id === uid) role = 'leader';
    else if (info.admin_ids && info.admin_ids.includes(uid)) role = 'admin';
    base.role = role;
    base.roleText = role === 'leader' ? '负责人' : role === 'admin' ? '管理员' : '成员';
  }
  return base;
}

function formatJoinClubCardData(info, uid, joined = []) {
  const data = formatClubCardData(info);
  const pending = (info.pending_members || []).some(m => m.user_id === uid);
  const rejected = info.rejected_members ? info.rejected_members[uid] : '';
  const join_status = joined.includes(info.club_id)
    ? 'joined'
    : pending
    ? 'pending'
    : rejected
    ? 'rejected'
    : 'apply';
  data.join_status = join_status;
  data.rejected_reason = rejected;
  return data;
}

module.exports = {
  formatClubStats,
  formatClubCardData,
  formatJoinClubCardData
};
