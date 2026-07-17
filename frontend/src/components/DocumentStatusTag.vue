<template>
  <ATag :color="statusMeta.color">{{ statusMeta.label }}</ATag>
</template>

<script setup>
/** 功能：根据文档状态值渲染统一的状态标签。 */
import { computed } from 'vue';

import { getDocumentStatusMeta } from '@/utils/document-status';

const props = defineProps({
  status: {
    type: String,
    default: '',
  },
});

/** 状态展示信息。 */
const statusMeta = computed(() => getDocumentStatusMeta(props.status));
</script>
