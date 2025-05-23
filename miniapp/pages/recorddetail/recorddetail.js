Page({
  data: {
    record: null
  },
  onLoad(options) {
    if (options.data) {
      try {
        const rec = JSON.parse(decodeURIComponent(options.data));
        this.setData({ record: rec });
      } catch (e) {}
    }
  }
});
