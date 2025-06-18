function calcAge(birth) {
  const d = new Date(birth);
  if (isNaN(d)) return '';
  const diff = Date.now() - d.getTime();
  return Math.floor(diff / (365 * 24 * 60 * 60 * 1000));
}

function genderText(g) {
  if (!g) return '';
  if (g === 'M' || g === 'Male' || g === '男') return '男';
  if (g === 'F' || g === 'Female' || g === '女') return '女';
  return g;
}

function formatExtraLines(info) {
  const line1 = [];
  const gender = genderText(info.gender);
  if (gender) line1.push(gender);
  const age = calcAge(info.birth);
  if (age) line1.push(`${age}岁`);

  const line2 = [];
  if (info.handedness) line2.push(info.handedness);
  if (info.backhand) line2.push(info.backhand);

  return { line1: line1.join('·'), line2: line2.join('·') };
}

module.exports = { calcAge, genderText, formatExtraLines };
