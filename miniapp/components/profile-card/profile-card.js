Component({
  properties: {
    user: {
      type: Object,
      value: null
    },
    placeholder: String
  },
  methods: {
    edit() {
      this.triggerEvent('edit');
    }
  }
});
