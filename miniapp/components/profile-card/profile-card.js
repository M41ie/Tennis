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
    info: String,
    info2: String,
    showRoleTag: {
      type: Boolean,
      value: true
    },
    roleInInfo: {
      type: Boolean,
      value: false
    }
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
