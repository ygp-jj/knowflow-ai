<template>
  <ADrawer
    :open="open"
    :title="detail?.file_name || '文档详情'"
    width="720"
    @close="$emit('close')"
  >
    <ASkeleton v-if="loading" active :paragraph="{ rows: 7 }" />
    <div v-else-if="detail" class="detail-panel">
      <div class="detail-grid">
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
          <span>{{ formatFileType(detail.file_type, detail.file_name) }}</span>
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
          <span>{{ detail.chunk_count ?? 0 }}</span>
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

      <section class="chunk-section">
        <div class="chunk-section__header">
          <div>
            <h3>文档切片</h3>
            <p>展示解析切片结果，便于核对 chunk 内容与页码。</p>
          </div>
          <AButton
            size="small"
            :loading="chunksLoading"
            :disabled="!canLoadChunks"
            @click="reloadChunks"
          >
            刷新切片
          </AButton>
        </div>

        <AAlert
          v-if="!canLoadChunks"
          type="info"
          show-icon
          message="当前文档尚未完成切片，可等待状态变为「已切片」后再查看。"
        />

        <ASpin v-else :spinning="chunksLoading">
          <AEmpty
            v-if="!chunksLoading && chunkItems.length === 0"
            description="暂无切片数据"
          />
          <div v-else class="chunk-list">
            <article
              v-for="chunk in chunkItems"
              :key="chunk.id"
              class="chunk-card"
            >
              <div class="chunk-card__meta">
                <strong>#{{ chunk.chunk_index }}</strong>
                <span>页码：{{ chunk.page_number ?? '—' }}</span>
                <span>Token：{{ chunk.token_count ?? 0 }}</span>
                <span>ID：{{ chunk.id }}</span>
              </div>
              <pre class="chunk-card__content">{{ chunk.content }}</pre>
            </article>
          </div>

          <div v-if="chunkTotal > 0" class="chunk-pagination">
            <APagination
              size="small"
              :current="chunkPage"
              :page-size="chunkPageSize"
              :total="chunkTotal"
              :show-size-changer="true"
              :page-size-options="['5', '10', '20']"
              :show-total="(total) => `共 ${total} 条切片`"
              @change="handleChunkPaginationChange"
            />
          </div>
        </ASpin>
      </section>
    </div>
    <AEmpty v-else description="暂无详情数据" />
  </ADrawer>
</template>

<script setup>
/** 功能：展示文档详情，并分页预览已落库的文档切片。 */
import { computed, ref, watch } from 'vue';
import { message } from 'ant-design-vue';

import DocumentStatusTag from './DocumentStatusTag.vue';
import { fetchDocumentChunks } from '@/services/document-service';
import { normalizeErrorMessage } from '@/utils/api';
import { formatDateTime, formatFileSize, formatFileType } from '@/utils/formatters';

const props = defineProps({
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

/** 切片列表。 */
const chunkItems = ref([]);
/** 切片总数。 */
const chunkTotal = ref(0);
/** 切片当前页。 */
const chunkPage = ref(1);
/** 切片分页大小。 */
const chunkPageSize = ref(5);
/** 切片加载状态。 */
const chunksLoading = ref(false);

/** 是否允许加载切片（已有切片数或已进入切片终态）。 */
const canLoadChunks = computed(() => {
  if (!props.detail) {
    return false;
  }

  /** 文档状态。 */
  const status = props.detail.status;
  /** 后端记录的切片数。 */
  const chunkCount = Number(props.detail.chunk_count || 0);
  return chunkCount > 0 || ['chunked', 'embedding', 'indexed'].includes(status);
});

watch(
  () => [props.open, props.detail?.id, props.detail?.chunk_count, props.detail?.status],
  async ([isOpen]) => {
    if (!isOpen || !props.detail?.id) {
      resetChunks();
      return;
    }

    chunkPage.value = 1;
    if (canLoadChunks.value) {
      await loadChunks();
    } else {
      resetChunks();
    }
  },
);

/**
 * 清空切片展示状态。
 * @returns {void}
 */
function resetChunks() {
  chunkItems.value = [];
  chunkTotal.value = 0;
  chunkPage.value = 1;
}

/**
 * 分页加载文档切片。
 * @returns {Promise<void>}
 */
async function loadChunks() {
  if (!props.detail?.id || !canLoadChunks.value) {
    return;
  }

  chunksLoading.value = true;

  try {
    /** 切片接口响应。 */
    const result = await fetchDocumentChunks({
      documentId: props.detail.id,
      page: chunkPage.value,
      pageSize: chunkPageSize.value,
    });

    chunkItems.value = result.items || [];
    chunkTotal.value = result.total || 0;
    chunkPage.value = result.page || chunkPage.value;
    chunkPageSize.value = result.page_size || chunkPageSize.value;
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    chunksLoading.value = false;
  }
}

/**
 * 手动刷新切片列表。
 * @returns {Promise<void>}
 */
async function reloadChunks() {
  await loadChunks();
}

/**
 * 切片分页变化（页码或 pageSize）。
 * @param {number} page 新页码。
 * @param {number} pageSize 新分页大小。
 * @returns {Promise<void>}
 */
async function handleChunkPaginationChange(page, pageSize) {
  /** 目标页码。 */
  const nextPage = page;
  /** 目标分页大小。 */
  const nextPageSize = pageSize || chunkPageSize.value;

  if (nextPage === chunkPage.value && nextPageSize === chunkPageSize.value) {
    return;
  }

  chunkPage.value = nextPage;
  chunkPageSize.value = nextPageSize;
  await loadChunks();
}
</script>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.chunk-section__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.chunk-section__header h3 {
  margin: 0;
  font-size: 16px;
}

.chunk-section__header p {
  margin: 4px 0 0;
  color: #667085;
  font-size: 13px;
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chunk-card {
  border: 1px solid #e5e7eb;
  background: #fafafa;
  padding: 12px 14px;
}

.chunk-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
  color: #667085;
  font-size: 12px;
}

.chunk-card__content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.55;
  color: #1f2937;
}

.chunk-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
