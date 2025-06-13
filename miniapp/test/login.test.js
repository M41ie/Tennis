const simulate = require('miniprogram-simulate');
const path = require('path');

test('login page loads with empty fields', () => {
  const id = simulate.load(path.join(__dirname, '../pages/login/index'), 'page');
  const comp = simulate.render(id);
  comp.attach(document.createElement('parent-wrapper'));
  expect(comp.data.loginId).toBe('');
  expect(comp.data.loginPw).toBe('');
});
