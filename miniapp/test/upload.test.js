const simulate = require('miniprogram-simulate');
const path = require('path');
const store = require('../store/store');

test('avatar upload and submit', async () => {
  global.getApp = () => ({ globalData: { BASE_URL: 'http://server' } });
  store.token = 'TOKEN';
  store.userId = 'u1';

  global.wx = {
    uploadFile: jest.fn(opts => {
      opts.success({ statusCode: 200, data: JSON.stringify({ url: 'http://server/uploads/a.png' }) });
    }),
    request: jest.fn(opts => {
      opts.success({ statusCode: 200, data: {} });
    }),
    showLoading: jest.fn(),
    hideLoading: jest.fn(),
    showToast: jest.fn(),
    navigateBack: jest.fn(),
    setStorageSync: jest.fn(),
    removeStorageSync: jest.fn()
  };

  const id = simulate.load(path.join(__dirname, '../pages/editprofile/editprofile'), 'page');
  const comp = simulate.render(id);
  comp.attach(document.createElement('parent-wrapper'));

  comp.setData({
    userId: 'u1',
    name: 'U1',
    genderIndex: 1,
    birth: '1990-01-01',
    handIndex: 1,
    backhandIndex: 1,
    region: ['A', 'B', 'C'],
    regionString: 'A B C',
    avatar: 'wxfile://tmp.png',
    tempAvatar: 'wxfile://tmp.png'
  });

  await comp.instance.submit();

  expect(wx.uploadFile).toHaveBeenCalled();
  const putCall = wx.request.mock.calls.find(c => c[0].method === 'PUT');
  expect(putCall).toBeTruthy();
  expect(wx.navigateBack).toHaveBeenCalled();
});
