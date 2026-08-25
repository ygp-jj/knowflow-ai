<template>
  <div class="page-shell">
    <section class="page-banner">
      <div>
        <h2 class="page-banner__title">文档管理</h2>
        <p class="page-banner__desc">
          统一管理知识库下的文档上传、手动切片、向量化、状态查看、详情浏览、切片预览、重命名、下载和删除。
        </p>
      </div>
      <div class="page-banner__meta">
        <div class="page-banner__meta-card">
          <label>文档总数</label>
          <strong>{{ total }}</strong>
        </div>
        <div class="page-banner__meta-card">
          <label>当前页条目</label>
          <strong>{{ items.length }}</strong>
        </div>
        <div class="page-banner__meta-card">
          <label>知识库筛选</label>
          <strong>{{ activeKnowledgeBaseName }}</strong>
        </div>
        <div class="page-banner__meta-card">
          <label>下载方式</label>
          <strong>后端流式</strong>
        </div>
      </div>
    </section>

    <ACard class="panel-card" :bordered="false">
      <div class="toolbar-row">
        <div class="toolbar-row__filters">
          <ASelect
            v-model:value="selectedKnowledgeBaseId"
            allow-clear
            style="min-width: 260px"
            placeholder="按知识库筛选文档"
            :loading="optionsLoading"
            :options="knowledgeBaseOptions"
            :field-names="{ label: 'name', value: 'id' }"
            @change="handleKnowledgeBaseFilterChange"
          />
          <ATag color="processing">上传接口使用 multipart/form-data</ATag>
        </div>
        <div class="toolbar-row__actions">
          <AButton @click="handleRefresh">
            <template #icon>
              <ReloadOutlined />
            </template>
            刷新
          </AButton>
          <AButton type="primary" @click="openUploadModal">
            <template #icon>
              <UploadOutlined />
            </template>
            上传文档
          </AButton>
        </div>
      </div>

      <ATable
        row-key="id"
        :columns="columns"
        :data-source="items"
        :loading="listLoading"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'file_name'">
            <div class="stack-cell">
              <strong>{{ record.file_name }}</strong>
              <small>ID: {{ record.id }}</small>
            </div>
          </template>

          <template v-else-if="column.key === 'knowledge_base_id'">
            {{ resolveKnowledgeBaseName(record.knowledge_base_id) }}
          </template>

          <template v-else-if="column.key === 'file_type'">
            {{ formatFileType(record.file_type, record.file_name) }}
          </template>

          <template v-else-if="column.key === 'file_size'">
            {{ formatFileSize(record.file_size) }}
          </template>

          <template v-else-if="column.key === 'status'">
            <DocumentStatusTag :status="record.status" />
          </template>

          <template v-else-if="column.key === 'chunk_count'">
            {{ record.chunk_count ?? 0 }}
          </template>

          <template v-else-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>

          <template v-else-if="column.key === 'updated_at'">
            {{ formatDateTime(record.updated_at) }}
          </template>

          <template v-else-if="column.key === 'actions'">
            <ASpace wrap>
              <AButton type="link" @click="openDetailDrawer(record)">详情</AButton>
              <AButton
                type="link"
                :disabled="!canStartChunk(record) || Boolean(chunkingIds[record.id])"
                :loading="Boolean(chunkingIds[record.id])"
                @click="handleChunk(record)"
              >
                {{ getChunkActionLabel(record) }}
              </AButton>
              <AButton
                type="link"
                :disabled="!canStartEmbed(record) || Boolean(embeddingIds[record.id])"
                :loading="Boolean(embeddingIds[record.id])"
                @click="handleEmbed(record)"
              >
                {{ getEmbedActionLabel(record) }}
              </AButton>
              <AButton type="link" @click="openRenameModal(record)">重命名</AButton>
              <AButton type="link" @click="handleDownload(record)">下载</AButton>
              <AButton danger type="link" @click="handleDelete(record)">删除</AButton>
            </ASpace>
          </template>
        </template>
      </ATable>
    </ACard>

    <DocumentUploadModal
      :open="uploadVisible"
      :confirm-loading="uploadSubmitting"
      :knowledge-base-options="knowledgeBaseOptions"
      :default-knowledge-base-id="selectedKnowledgeBaseId"
      @cancel="closeUploadModal"
      @submit="handleUpload"
    />

    <DocumentRenameModal
      :open="renameVisible"
      :initial-name="renamingRecord?.file_name || ''"
      :confirm-loading="renameSubmitting"
      @cancel="closeRenameModal"
      @submit="handleRename"
    />

    <DocumentDetailDrawer
      :open="detailVisible"
      :loading="detailLoading"
      :detail="activeDocument"
      @close="closeDetailDrawer"
    />
  </div>
</template>

<script setup>
/** 功能：承载文档管理页面的筛选、上传、手动切片、详情、下载、重命名和删除交互。 */
import { computed, onMounted, ref } from 'vue';
import { Modal, message } from 'ant-design-vue';
import { ReloadOutlined, UploadOutlined } from '@ant-design/icons-vue';

import DocumentDetailDrawer from '@/components/DocumentDetailDrawer.vue';
import DocumentRenameModal from '@/components/DocumentRenameModal.vue';
import DocumentStatusTag from '@/components/DocumentStatusTag.vue';
import DocumentUploadModal from '@/components/DocumentUploadModal.vue';
import {
  chunkDocument,
  createDocument,
  deleteDocument,
  downloadDocument,
  embedDocument,
  fetchDocumentDetail,
  fetchDocumentList,
  updateDocument,
} from '@/services/document-service';
import { fetchKnowledgeBaseList } from '@/services/knowledge-base-service';
import { normalizeErrorMessage } from '@/utils/api';
import { formatDateTime, formatFileSize, formatFileType } from '@/utils/formatters';

/** 文档表格列定义。 */
const columns = [
  { title: '文档名称', dataIndex: 'file_name', key: 'file_name', width: 240 },
  { title: '所属知识库', dataIndex: 'knowledge_base_id', key: 'knowledge_base_id', width: 180 },
  { title: '文件类型', dataIndex: 'file_type', key: 'file_type', width: 120 },
  { title: '文件大小', dataIndex: 'file_size', key: 'file_size', width: 120 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '切片数', dataIndex: 'chunk_count', key: 'chunk_count', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170 },
  { title: '操作', key: 'actions', width: 430, fixed: 'right' },
];

/** 当前页文档列表。 */
const items = ref([]);
/** 文档总数。 */
const total = ref(0);
/** 当前页码。 */
const page = ref(1);
/** 当前分页大小。 */
const pageSize = ref(10);
/** 列表加载状态。 */
const listLoading = ref(false);
/** 详情加载状态。 */
const detailLoading = ref(false);
/** 知识库选项加载状态。 */
const optionsLoading = ref(false);
/** 当前文档详情。 */
const activeDocument = ref(null);
/** 知识库下拉选项。 */
const knowledgeBaseOptions = ref([]);
/** 当前知识库筛选值。 */
const selectedKnowledgeBaseId = ref(null);
/** 上传弹窗开关。 */
const uploadVisible = ref(false);
/** 上传中状态。 */
const uploadSubmitting = ref(false);
/** 重命名弹窗开关。 */
const renameVisible = ref(false);
/** 重命名中状态。 */
const renameSubmitting = ref(false);
/** 详情抽屉开关。 */
const detailVisible = ref(false);
/** 当前重命名对象。 */
const renamingRecord = ref(null);
/** 正在触发切片的文档 ID 集合。 */
const chunkingIds = ref({});
/** 正在触发向量化的文档 ID 集合。 */
const embeddingIds = ref({});

/** 分页配置对象。 */
const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条`,
}));

/** 当前筛选知识库名称。 */
const activeKnowledgeBaseName = computed(() => {
  if (!selectedKnowledgeBaseId.value) {
    return '全部';
  }

  /** 命中的知识库对象。 */
  const target = knowledgeBaseOptions.value.find((item) => item.id === selectedKnowledgeBaseId.value);
  return target?.name || `#${selectedKnowledgeBaseId.value}`;
});

onMounted(async () => {
  try {
    await Promise.all([
      loadKnowledgeBaseOptions(),
      loadDocumentList(),
    ]);
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
});

/**
 * 加载知识库下拉选项。
 * @returns {Promise<void>}
 */
async function loadKnowledgeBaseOptions() {
  optionsLoading.value = true;

  try {
    /** 选项响应数据。 */
    const result = await fetchKnowledgeBaseList({
      page: 1,
      pageSize: 100,
    });

    knowledgeBaseOptions.value = result.items || [];
  } finally {
    optionsLoading.value = false;
  }
}

/**
 * 加载文档分页列表。
 * @param {{ page?: number, pageSize?: number, knowledgeBaseId?: number | null }} filters 查询条件。
 * @returns {Promise<void>}
 */
async function loadDocumentList(filters = {}) {
  listLoading.value = true;

  try {
    /** 当前请求参数。 */
    const params = {
      page: filters.page || page.value,
      pageSize: filters.pageSize || pageSize.value,
      knowledgeBaseId: Object.prototype.hasOwnProperty.call(filters, 'knowledgeBaseId')
        ? filters.knowledgeBaseId
        : selectedKnowledgeBaseId.value,
    };
    /** 列表响应数据。 */
    const result = await fetchDocumentList(params);

    items.value = result.items || [];
    total.value = result.total || 0;
    page.value = Number(result.page) || params.page;
    pageSize.value = Number(result.page_size) || params.pageSize;
  } finally {
    listLoading.value = false;
  }
}

/**
 * 根据知识库 ID 解析名称。
 * @param {number} id 知识库 ID。
 * @returns {string}
 */
function resolveKnowledgeBaseName(id) {
  /** 命中的知识库对象。 */
  const target = knowledgeBaseOptions.value.find((item) => item.id === id);
  return target?.name || `知识库 #${id}`;
}

/**
 * 刷新当前文档列表。
 * @returns {Promise<void>}
 */
async function handleRefresh() {
  try {
    await loadDocumentList({
      page: page.value,
      pageSize: pageSize.value,
      knowledgeBaseId: selectedKnowledgeBaseId.value,
    });
    message.success('文档列表已刷新');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}

/**
 * 切换知识库筛选。
 * @returns {Promise<void>}
 */
async function handleKnowledgeBaseFilterChange() {
  try {
    await loadDocumentList({
      page: 1,
      pageSize: pageSize.value,
      knowledgeBaseId: selectedKnowledgeBaseId.value,
    });
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}

/**
 * 打开上传弹窗。
 * @returns {void}
 */
function openUploadModal() {
  uploadVisible.value = true;
}

/**
 * 关闭上传弹窗。
 * @returns {void}
 */
function closeUploadModal() {
  uploadVisible.value = false;
}

/**
 * 提交上传操作。
 * @param {{ knowledgeBaseId: number | null, file: File | null }} payload 上传参数。
 * @returns {Promise<void>}
 */
async function handleUpload(payload) {
  if (!payload.knowledgeBaseId) {
    message.warning('请选择所属知识库');
    return;
  }

  if (!payload.file) {
    message.warning('请选择要上传的文件');
    return;
  }

  uploadSubmitting.value = true;

  try {
    await createDocument({
      knowledgeBaseId: payload.knowledgeBaseId,
      file: payload.file,
    });
    uploadVisible.value = false;
    selectedKnowledgeBaseId.value = payload.knowledgeBaseId;
    await loadDocumentList({
      page: 1,
      pageSize: pageSize.value,
      knowledgeBaseId: payload.knowledgeBaseId,
    });
    message.success('文档上传成功，请点击「切片」开始解析');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    uploadSubmitting.value = false;
  }
}

/**
 * 打开重命名弹窗。
 * @param {any} record 当前文档记录。
 * @returns {void}
 */
function openRenameModal(record) {
  renamingRecord.value = record;
  renameVisible.value = true;
}

/**
 * 关闭重命名弹窗。
 * @returns {void}
 */
function closeRenameModal() {
  renameVisible.value = false;
}

/**
 * 提交重命名操作。
 * @param {{ file_name: string }} payload 新文件名参数。
 * @returns {Promise<void>}
 */
async function handleRename(payload) {
  if (!payload.file_name) {
    message.warning('请输入新的文档名称');
    return;
  }

  renameSubmitting.value = true;

  try {
    await updateDocument({
      id: renamingRecord.value.id,
      file_name: payload.file_name,
    });
    await loadDocumentList();
    renameVisible.value = false;
    message.success('文档名称已更新');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    renameSubmitting.value = false;
  }
}

/**
 * 是否允许手动触发切片。
 * @param {any} record 文档记录。
 * @returns {boolean}
 */
function canStartChunk(record) {
  return ['uploaded', 'failed', 'chunked', 'embedded'].includes(record?.status);
}

/**
 * 切片按钮文案。
 * @param {any} record 文档记录。
 * @returns {string}
 */
function getChunkActionLabel(record) {
  if (record?.status === 'chunked' || record?.status === 'embedded') {
    return '重新切片';
  }
  if (['parsing', 'chunking', 'embedding'].includes(record?.status)) {
    return '切片中';
  }
  return '切片';
}

/**
 * 是否允许手动触发向量化（需已有切片）。
 * @param {any} record 文档记录。
 * @returns {boolean}
 */
function canStartEmbed(record) {
  if (!['chunked', 'embedded', 'failed'].includes(record?.status)) {
    return false;
  }
  return Number(record?.chunk_count || 0) > 0;
}

/**
 * 向量化按钮文案。
 * @param {any} record 文档记录。
 * @returns {string}
 */
function getEmbedActionLabel(record) {
  if (record?.status === 'embedded') {
    return '重新向量化';
  }
  if (record?.status === 'embedding') {
    return '向量化中';
  }
  return '向量化';
}

/**
 * 手动触发文档切片（不轮询列表，完成后请点刷新查看状态）。
 * @param {any} record 当前文档记录。
 * @returns {Promise<void>}
 */
async function handleChunk(record) {
  if (!canStartChunk(record)) {
    message.warning('当前状态不可切片');
    return;
  }

  chunkingIds.value = {
    ...chunkingIds.value,
    [record.id]: true,
  };

  try {
    await chunkDocument(record.id);
    message.success('切片任务已提交，请稍后点击「刷新」查看结果');
    await loadDocumentList({
      page: page.value,
      pageSize: pageSize.value,
      knowledgeBaseId: selectedKnowledgeBaseId.value,
    });
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    /** 复制一份 loading 映射后移除当前文档。 */
    const nextChunkingIds = { ...chunkingIds.value };
    delete nextChunkingIds[record.id];
    chunkingIds.value = nextChunkingIds;
  }
}

/**
 * 手动触发文档向量化（不轮询；完成后点刷新查看 embedded / failed）。
 * @param {any} record 当前文档记录。
 * @returns {Promise<void>}
 */
async function handleEmbed(record) {
  if (!canStartEmbed(record)) {
    message.warning('当前状态不可向量化，请先完成切片');
    return;
  }

  embeddingIds.value = {
    ...embeddingIds.value,
    [record.id]: true,
  };

  try {
    await embedDocument(record.id);
    message.success('向量化任务已提交，请稍后点击「刷新」查看结果');
    await loadDocumentList({
      page: page.value,
      pageSize: pageSize.value,
      knowledgeBaseId: selectedKnowledgeBaseId.value,
    });
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    const nextEmbeddingIds = { ...embeddingIds.value };
    delete nextEmbeddingIds[record.id];
    embeddingIds.value = nextEmbeddingIds;
  }
}

/**
 * 打开详情抽屉。
 * @param {any} record 当前文档记录。
 * @returns {Promise<void>}
 */
async function openDetailDrawer(record) {
  detailVisible.value = true;
  detailLoading.value = true;

  try {
    activeDocument.value = await fetchDocumentDetail(record.id);
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    detailLoading.value = false;
  }
}

/**
 * 关闭详情抽屉。
 * @returns {void}
 */
function closeDetailDrawer() {
  detailVisible.value = false;
}

/**
 * 下载文档文件。
 * @param {any} record 当前文档记录。
 * @returns {Promise<void>}
 */
async function handleDownload(record) {
  try {
    /** 下载得到的二进制数据。 */
    const blob = await downloadDocument(record.id);
    /** 浏览器下载地址。 */
    const downloadUrl = window.URL.createObjectURL(blob);
    /** 临时下载节点。 */
    const anchor = document.createElement('a');

    anchor.href = downloadUrl;
    anchor.download = record.file_name;
    anchor.click();

    window.URL.revokeObjectURL(downloadUrl);
    message.success('文档下载已开始');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}

/**
 * 删除文档记录。
 * @param {any} record 当前文档记录。
 * @returns {void}
 */
function handleDelete(record) {
  Modal.confirm({
    title: `确定删除“${record.file_name}”吗？`,
    content: '该操作会同步删除数据库记录和 MinIO 中的对象文件。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await deleteDocument(record.id);
        await loadDocumentList();
        if (activeDocument.value?.id === record.id) {
          activeDocument.value = null;
        }
        message.success('文档已删除');
      } catch (error) {
        message.error(normalizeErrorMessage(error));
      }
    },
  });
}

/**
 * 响应分页变化。
 * @param {{ current: number, pageSize: number }} pager 分页参数。
 * @returns {Promise<void>}
 */
async function handleTableChange(pager) {
  // 列表加载中忽略 Table 因 dataSource 回写触发的二次 change，避免整页反复刷请求。
  if (listLoading.value) {
    return;
  }

  /** 目标页码（缺省时沿用当前页，避免 undefined 误触发重载）。 */
  const nextPage = Number(pager?.current) || page.value;
  /** 目标分页大小。 */
  const nextPageSize = Number(pager?.pageSize) || pageSize.value;

  // 分页配置回写后 Table 可能再次触发 change，页码未变则跳过，避免重复请求。
  if (nextPage === page.value && nextPageSize === pageSize.value) {
    return;
  }

  try {
    await loadDocumentList({
      page: nextPage,
      pageSize: nextPageSize,
      knowledgeBaseId: selectedKnowledgeBaseId.value,
    });
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}
</script>
