<template>
  <AModal
    :open="open"
    :confirm-loading="confirmLoading"
    title="上传文档"
    destroy-on-close
    ok-text="上传"
    cancel-text="取消"
    @cancel="handleCancel"
    @ok="handleOk"
  >
    <AForm layout="vertical">
      <AFormItem label="所属知识库" required>
        <ASelect
          v-model:value="formState.knowledgeBaseId"
          :options="knowledgeBaseOptions"
          :field-names="{ label: 'name', value: 'id' }"
          placeholder="请选择知识库"
          show-search
          option-filter-prop="name"
        />
      </AFormItem>
      <AFormItem label="文档文件" required>
        <UploadDragger
          :before-upload="handleBeforeUpload"
          :file-list="formState.fileList"
          :max-count="1"
          @remove="handleRemove"
        >
          <p class="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p class="ant-upload-text">点击或拖拽文件到这里上传</p>
          <p class="ant-upload-hint">支持 PDF、Word、TXT、Markdown 等文档格式</p>
        </UploadDragger>
      </AFormItem>
    </AForm>
  </AModal>
</template>

<script setup>
/** 功能：提供文档上传弹窗，选择所属知识库并暂存待上传文件。 */
import { reactive, watch } from 'vue';
import { InboxOutlined } from '@ant-design/icons-vue';
import { UploadDragger } from 'ant-design-vue';

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  confirmLoading: {
    type: Boolean,
    default: false,
  },
  knowledgeBaseOptions: {
    type: Array,
    default: () => [],
  },
  defaultKnowledgeBaseId: {
    type: Number,
    default: null,
  },
});

const emit = defineEmits(['cancel', 'submit']);

/** 上传表单状态。 */
const formState = reactive({
  knowledgeBaseId: null,
  fileList: [],
  rawFile: null,
});

watch(
  () => props.open,
  () => {
    if (!props.open) {
      return;
    }

    formState.knowledgeBaseId = props.defaultKnowledgeBaseId;
    formState.fileList = [];
    formState.rawFile = null;
  },
  { immediate: true },
);

/**
 * 拦截自动上传并缓存文件。
 * @param {File} file 当前文件。
 * @returns {boolean}
 */
function handleBeforeUpload(file) {
  formState.fileList = [
    {
      uid: file.uid,
      name: file.name,
      status: 'done',
      originFileObj: file,
    },
  ];
  formState.rawFile = file;
  return false;
}

/**
 * 清理文件列表。
 * @returns {void}
 */
function handleRemove() {
  formState.fileList = [];
  formState.rawFile = null;
}

/**
 * 关闭弹窗。
 * @returns {void}
 */
function handleCancel() {
  emit('cancel');
}

/**
 * 提交上传参数。
 * @returns {void}
 */
function handleOk() {
  emit('submit', {
    knowledgeBaseId: formState.knowledgeBaseId,
    file: formState.rawFile,
  });
}
</script>
