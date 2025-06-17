const { zh_CN: t } = require('../../utils/locales');
Component({
  properties: {
    club: Object,
    joinStatus: String,
    showRoleTag: {
      type: Boolean,
      value: false
    },
    reason: String
  },
  data: { t },
  methods: {
    tapCard() {
      this.triggerEvent('tap', { club: this.data.club });
    },
    onJoin() {
      this.triggerEvent('join', { club: this.data.club });
    },
    onViewReject() {
      this.triggerEvent('viewreject', { club: this.data.club, reason: this.data.reason });
    }
  }
});
