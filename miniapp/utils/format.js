function formatRating(value) {
  if (value == null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(3);
}

function formatGames(value) {
  if (value == null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(2);
}

function withBase(path) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return getApp().globalData.BASE_URL + path;
}

function formatScoreDiff(value) {
  const num = Number(value);
  if (!value || Number.isNaN(num)) {
    return { display: '0.000', cls: 'neutral' };
  }
  const abs = Math.abs(num).toFixed(3);
  const sign = num > 0 ? '+' : num < 0 ? '-' : '';
  const cls = num > 0 ? 'pos' : num < 0 ? 'neg' : 'neutral';
  return { display: sign + abs, cls };
}

module.exports = { formatRating, formatGames, withBase, formatScoreDiff };
