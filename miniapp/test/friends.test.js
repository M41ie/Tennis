const simulate = require('miniprogram-simulate');
const path = require('path');
const store = require('../store/store');
const friendService = require('../services/friend');

// mock getApp and wx
global.getApp = () => ({ globalData: { BASE_URL: 'http://server' } });

global.wx = { navigateTo: jest.fn() };

const sampleData = [
  {
    user_id: 'f1',
    name: 'F1',
    avatar: '/f1.png',
    singles_weight: 1,
    singles_wins: 1,
    doubles_weight: 1,
    doubles_wins: 0,
    partner_games: 1,
    partner_wins: 1,
  },
  {
    user_id: 'f2',
    name: 'F2',
    avatar: '/f2.png',
    singles_weight: 1,
    singles_wins: 0,
  },
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
  expect(items[0].querySelectorAll('.icon').length).toBe(3);
  // verify partner information is displayed when available
  const partnerText1 = items[0].querySelectorAll('.text')[2].innerHTML;
  expect(partnerText1).toBe('搭档1场');
  // verify absence of partner information displays fallback text
  const partnerText2 = items[1].querySelectorAll('.text')[2].innerHTML;
  expect(partnerText2).toBe('尚未搭档');
  const summary = comp.dom.querySelector('.summary').innerHTML;
  expect(summary).toBe('您共与2位球友对战/搭档过：');
});
