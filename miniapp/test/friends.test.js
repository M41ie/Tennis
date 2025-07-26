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
    singles_score_diff: 2,
    doubles_weight: 1,
    doubles_wins: 0,
    doubles_score_diff: -1,
    partner_games: 1,
    partner_wins: 1,
    partner_score_diff: 3,
  },
  {
    user_id: 'f2',
    name: 'F2',
    avatar: '/f2.png',
    singles_weight: 1,
    singles_wins: 0,
    singles_score_diff: -2,
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
  const score1 = items[0].querySelectorAll('.score')[0].innerHTML;
  expect(score1).toBe('+2.000');
  const score2 = items[1].querySelectorAll('.score')[0].innerHTML;
  expect(score2).toBe('-2.000');
  const summary = comp.dom.querySelector('.summary').innerHTML;
  expect(summary).toBe('您与2位球友交手或搭档过：');
});
