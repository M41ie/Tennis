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
    },
    info: String
  },
  methods: {
    edit() {
      this.triggerEvent('edit');
    },
    tapCard() {
      this.triggerEvent('cardtap');
    }
  }
});
