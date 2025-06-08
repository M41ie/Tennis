Component({
  properties: {
    record: Object,
    doubles: {
      type: Boolean,
      value: false
    },
    showActions: {
      type: Boolean,
      value: false
    },
    index: Number,
    statusText: String,
    canConfirm: Boolean,
    canReject: Boolean,
    canApprove: Boolean,
    canVeto: Boolean
  },
  methods: {
    onConfirm() {
      this.triggerEvent('confirm', { record: this.data.record, index: this.data.index });
    },
    onReject() {
      this.triggerEvent('reject', { record: this.data.record, index: this.data.index });
    },
    onApprove() {
      this.triggerEvent('approve', { record: this.data.record, index: this.data.index });
    },
    onVeto() {
      this.triggerEvent('veto', { record: this.data.record, index: this.data.index });
    },
    onShare() {
      this.triggerEvent('share', { record: this.data.record, index: this.data.index });
    }
  }
});
