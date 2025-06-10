Component({
  properties: {
    user: {
      type: Object,
      value: null
    },
    placeholder: String,
    editable: {
      type: Boolean,
      value: true
    }
  },
  methods: {
    edit() {
      this.triggerEvent('edit');
    },
    tapCard() {
      this.triggerEvent('tap');
    }
  }
});
