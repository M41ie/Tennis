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

module.exports = { formatRating, formatGames, withBase };
