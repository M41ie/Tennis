const { formatRating } = require('../../utils/format');
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
    },
    fr(value) {
      return formatRating(value);
    }
  }
});
