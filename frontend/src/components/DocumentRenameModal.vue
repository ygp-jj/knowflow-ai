<template>
  <AModal
    :open="open"
    :confirm-loading="confirmLoading"
    title="重命名文档"
    destroy-on-close
    ok-text="保存"
    cancel-text="取消"
    @cancel="handleCancel"
    @ok="handleOk"
  >
    <AForm layout="vertical">
      <AFormItem label="文档名称" required>
        <AInput
          v-model:value="fileName"
          :maxlength="255"
          placeholder="请输入新的文档文件名"
          show-count
        />
      </AFormItem>
    </AForm>
  </AModal>
</template>

<script setup>
/** 功能：提供文档重命名弹窗表单。 */
import { ref, watch } from 'vue';

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  initialName: {
    type: String,
    default: '',
  },
  confirmLoading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['cancel', 'submit']);

/** 当前输入的文件名。 */
const fileName = ref('');

watch(
  () => [props.open, props.initialName],
  () => {
    if (!props.open) {
      return;
    }

    fileName.value = props.initialName || '';
  },
  { immediate: true },
);

/**
 * 关闭弹窗。
 * @returns {void}
 */
function handleCancel() {
  emit('cancel');
}

/**
 * 提交新文件名。
 * @returns {void}
 */
function handleOk() {
  emit('submit', {
    file_name: fileName.value.trim(),
  });
}
</script>
