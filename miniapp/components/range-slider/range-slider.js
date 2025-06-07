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
    innerMax: 0,
    trackWidth: 0,
    leftPos: 0,
    rightPos: 0,
    handleWidth: 30,
    handleRadius: 15,
    lastMove: 0
  },
  lifetimes: {
    attached() {
      const val = this.properties.value;
      const min = val.length && val[0] !== '' ? val[0] : this.properties.min;
      const max = val.length && val[1] !== '' ? val[1] : this.properties.max;
      this.setData({ innerMin: min, innerMax: max });
    },
    ready() {
      const query = this.createSelectorQuery();
      query.in(this).select('.range-track').boundingClientRect(rect => {
        const width = rect.width - this.data.handleWidth;
        this.setData({ trackWidth: width < 0 ? 0 : width }, () => {
          this.updatePositions();
        });
      }).exec();
    }
  },
  methods: {
    valueToPos(val) {
      const { min, max, trackWidth } = this.data;
      return ((val - min) / (max - min)) * trackWidth;
    },
    posToValue(pos) {
      const { min, max, step, trackWidth } = this.data;
      let value = min + (pos / trackWidth) * (max - min);
      value = Math.round(value / step) * step;
      value = Math.max(min, Math.min(max, value));
      return value;
    },
    updatePositions() {
      const leftPos = this.valueToPos(this.data.innerMin);
      const rightPos = this.valueToPos(this.data.innerMax);
      this.setData({ leftPos, rightPos });
    },
    onHandleMove(e) {
      const type = e.currentTarget.dataset.type;
      const now = Date.now();
      if (now - this.data.lastMove < 30) return;
      const pos = e.detail.x;
      this.setData({ lastMove: now });
      this.updateValue(type, pos, true);
    },
    onHandleEnd(e) {
      const type = e.currentTarget.dataset.type;
      const pos = e.detail.x;
      this.updateValue(type, pos, false);
    },
    updateValue(type, pos, moving) {
      const { leftPos, rightPos, step, innerMin, innerMax, min, max } = this.data;
      let val = this.posToValue(pos);
      if (type === 'min') {
        if (val > innerMax - step) val = innerMax - step;
        val = Math.max(min, val);
        this.setData({ innerMin: val, leftPos: this.valueToPos(val) });
      } else {
        if (val < innerMin + step) val = innerMin + step;
        val = Math.min(max, val);
        this.setData({ innerMax: val, rightPos: this.valueToPos(val) });
      }
      const payload = { value: [this.data.innerMin, this.data.innerMax] };
      this.triggerEvent(moving ? 'changing' : 'change', payload);
    }
  }
});
