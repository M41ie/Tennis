function formatRating(value) {
  if (value == null || value === '') return '--';
  const num = Number(value);
  if (Number.isNaN(num)) return '--';
  return num.toFixed(3);
}
module.exports = { formatRating };
