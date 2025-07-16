const simulate = require('miniprogram-simulate');
const path = require('path');
const store = require('../store/store');
const friendService = require('../services/friend');

// mock getApp and wx
global.getApp = () => ({ globalData: { BASE_URL: 'http://server' } });

global.wx = { navigateTo: jest.fn() };

const sampleData = [
  { user_id: 'f1', name: 'F1', avatar: '/f1.png', weight: 3, wins: 2, partner_games: 1 },
  { user_id: 'f2', name: 'F2', avatar: '/f2.png', weight: 1, wins: 0 }
];

friendService.getFriends = jest.fn().mockResolvedValue(sampleData);

async function loadPage() {
  const id = simulate.load(path.join(__dirname, '../pages/myfriends/myfriends'), 'page');
  const comp = simulate.render(id);
  comp.attach(document.createElement('parent-wrapper'));
  return comp;
}

test('friends page shows entries', async () => {
  store.userId = 'u1';
  const comp = await loadPage();
  await comp.instance.onShow();
  // wait for promise resolution
  await Promise.resolve();
  expect(friendService.getFriends).toHaveBeenCalledWith('u1');
  expect(comp.data.list.length).toBe(2);
  const items = comp.dom.querySelectorAll('.friend-item');
  expect(items.length).toBe(2);
  expect(items[0].querySelector('.name').innerHTML).toBe('F1');
  expect(items[1].querySelector('.name').innerHTML).toBe('F2');
});
