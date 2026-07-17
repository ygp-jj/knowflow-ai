<template>
  <AModal
    :open="open"
    :confirm-loading="confirmLoading"
    :title="modalTitle"
    destroy-on-close
    ok-text="保存"
    cancel-text="取消"
    @cancel="handleCancel"
    @ok="handleOk"
  >
    <AForm layout="vertical">
      <AFormItem label="知识库名称" required>
        <AInput
          v-model:value="formState.name"
          :maxlength="200"
          placeholder="例如：产品知识库"
          show-count
        />
      </AFormItem>
      <AFormItem label="描述说明">
        <ATextarea
          v-model:value="formState.description"
          :maxlength="500"
          :auto-size="{ minRows: 3, maxRows: 6 }"
          placeholder="说明该知识库的用途、文档范围和适用对象"
          show-count
        />
      </AFormItem>
    </AForm>
  </AModal>
</template>

<script setup>
/** 功能：提供知识库新建和编辑弹窗表单。 */
import { computed, reactive, watch } from 'vue';

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  mode: {
    type: String,
    default: 'create',
  },
  initialValues: {
    type: Object,
    default: () => ({
      name: '',
      description: '',
    }),
  },
  confirmLoading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['cancel', 'submit']);

/** 表单状态对象。 */
const formState = reactive({
  name: '',
  description: '',
});

/** 弹窗标题。 */
const modalTitle = computed(() => (props.mode === 'edit' ? '编辑知识库' : '新建知识库'));

watch(
  () => [props.open, props.initialValues],
  () => {
    if (!props.open) {
      return;
    }

    formState.name = props.initialValues?.name || '';
    formState.description = props.initialValues?.description || '';
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
 * 提交表单。
 * @returns {void}
 */
function handleOk() {
  emit('submit', {
    name: formState.name.trim(),
    description: formState.description.trim(),
  });
}
</script>
