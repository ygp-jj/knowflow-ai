<template>
  <ADrawer
    :open="open"
    :title="detail?.name || '知识库详情'"
    width="520"
    @close="$emit('close')"
  >
    <ASkeleton v-if="loading" active :paragraph="{ rows: 6 }" />
    <div v-else-if="detail" class="detail-grid">
      <div class="detail-item">
        <label>知识库 ID</label>
        <strong>#{{ detail.id }}</strong>
      </div>
      <div class="detail-item">
        <label>所有者</label>
        <span>{{ detail.owner_id }}</span>
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
        <label>描述说明</label>
        <span>{{ detail.description || '暂无说明' }}</span>
      </div>
    </div>
    <AEmpty v-else description="暂无详情数据" />
  </ADrawer>
</template>

<script setup>
/** 功能：展示知识库详情信息抽屉。 */
import { formatDateTime } from '@/utils/formatters';

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
