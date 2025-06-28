module.exports = function optimisticUpdate(ctx, key, id, requestFn) {
  const list = (ctx.data[key] || []).slice();
  const idx = list.findIndex(item => item.id === id);
  let removed;
  if (idx !== -1) {
    removed = list.splice(idx, 1)[0];
    ctx.setData({ [key]: list });
  }
  return requestFn().catch(err => {
    if (idx !== -1) {
      list.splice(idx, 0, removed);
      ctx.setData({ [key]: list });
    }
    wx.showToast({ duration: 4000,  title: '操作失败', icon: 'none' });
    return Promise.reject(err);
  });
};
