<template>
  <ADrawer
    :open="open"
    :title="detail?.file_name || '文档详情'"
    width="560"
    @close="$emit('close')"
  >
    <ASkeleton v-if="loading" active :paragraph="{ rows: 7 }" />
    <div v-else-if="detail" class="detail-grid">
      <div class="detail-item">
        <label>文档 ID</label>
        <strong>#{{ detail.id }}</strong>
      </div>
      <div class="detail-item">
        <label>所属知识库</label>
        <span>{{ detail.knowledge_base_id }}</span>
      </div>
      <div class="detail-item">
        <label>文件类型</label>
        <span>{{ detail.file_type }}</span>
      </div>
      <div class="detail-item">
        <label>文件大小</label>
        <span>{{ formatFileSize(detail.file_size) }}</span>
      </div>
      <div class="detail-item">
        <label>文档状态</label>
        <DocumentStatusTag :status="detail.status" />
      </div>
      <div class="detail-item">
        <label>切片数量</label>
        <span>{{ detail.chunk_count }}</span>
      </div>
      <div class="detail-item">
        <label>创建时间</label>
        <span>{{ formatDateTime(detail.created_at) }}</span>
      </div>
      <div class="detail-item">
        <label>更新时间</label>
        <span>{{ formatDateTime(detail.updated_at) }}</span>
      </div>
      <div class="detail-item" style="grid-column: 1 / -1">
        <label>错误信息</label>
        <span>{{ detail.error_message || '无' }}</span>
      </div>
    </div>
    <AEmpty v-else description="暂无详情数据" />
  </ADrawer>
</template>

<script setup>
/** 功能：展示文档详情、状态、大小和错误信息抽屉。 */
import DocumentStatusTag from './DocumentStatusTag.vue';
import { formatDateTime, formatFileSize } from '@/utils/formatters';

defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  detail: {
    type: Object,
    default: null,
  },
});

defineEmits(['close']);
</script>
