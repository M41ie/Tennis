Component({
  properties: {
    min: { type: Number, value: 0 },
    max: { type: Number, value: 100 },
    step: { type: Number, value: 1 },
    value: { type: Array, value: [] },
    activeColor: { type: String, value: '#07C160' },
    backgroundColor: { type: String, value: '#ccc' }
  },
  data: {
    innerMin: 0,
    innerMax: 0
  },
  lifetimes: {
    attached() {
      const val = this.properties.value;
      const min = val.length ? val[0] : this.properties.min;
      const max = val.length ? val[1] : this.properties.max;
      this.setData({ innerMin: min, innerMax: max });
    }
  },
  methods: {
    onChange(e) {
      const [min, max] = e.detail.value;
      this.setData({ innerMin: min, innerMax: max });
      this.triggerEvent('change', { value: [min, max] });
    },
    onChanging(e) {
      const [min, max] = e.detail.value;
      this.setData({ innerMin: min, innerMax: max });
      this.triggerEvent('changing', { value: [min, max] });
    }
  }
});
