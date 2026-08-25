<template>
  <div class="page-shell">
    <section class="page-banner">
      <div>
        <h2 class="page-banner__title">知识库管理</h2>
        <p class="page-banner__desc">
          管理当前登录用户的知识库，支持创建、分页浏览、详情查看、编辑和删除。
        </p>
      </div>
      <div class="page-banner__meta">
        <div class="page-banner__meta-card">
          <label>知识库总数</label>
          <strong>{{ total }}</strong>
        </div>
        <div class="page-banner__meta-card">
          <label>当前页条目</label>
          <strong>{{ items.length }}</strong>
        </div>
        <div class="page-banner__meta-card">
          <label>接口范围</label>
          <strong>CRUD</strong>
        </div>
      </div>
    </section>

    <ACard class="panel-card" :bordered="false">
      <div class="toolbar-row">
        <div class="toolbar-row__filters">
          <ATag color="blue">分页接口</ATag>
          <ATag color="cyan">统一响应</ATag>
          <ATag color="gold">删除前校验关联文档</ATag>
        </div>
        <div class="toolbar-row__actions">
          <AButton @click="handleRefresh">
            <template #icon>
              <ReloadOutlined />
            </template>
            刷新
          </AButton>
          <AButton type="primary" @click="openCreateModal">
            <template #icon>
              <PlusOutlined />
            </template>
            新建知识库
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
          <template v-if="column.key === 'name'">
            <div class="stack-cell">
              <strong>{{ record.name }}</strong>
              <small>ID: {{ record.id }}</small>
            </div>
          </template>

          <template v-else-if="column.key === 'description'">
            {{ record.description || '暂无说明' }}
          </template>

          <template v-else-if="column.key === 'created_at'">
            {{ formatDateTime(record.created_at) }}
          </template>

          <template v-else-if="column.key === 'updated_at'">
            {{ formatDateTime(record.updated_at) }}
          </template>

          <template v-else-if="column.key === 'actions'">
            <ASpace>
              <AButton type="link" @click="openDetailDrawer(record)">详情</AButton>
              <AButton type="link" @click="openEditModal(record)">编辑</AButton>
              <AButton danger type="link" @click="handleDelete(record)">删除</AButton>
            </ASpace>
          </template>
        </template>
      </ATable>
    </ACard>

    <KnowledgeBaseFormModal
      :open="formVisible"
      :mode="formMode"
      :initial-values="formInitialValues"
      :confirm-loading="formSubmitting"
      @cancel="closeFormModal"
      @submit="handleSubmit"
    />

    <KnowledgeBaseDetailDrawer
      :open="detailVisible"
      :loading="detailLoading"
      :detail="activeKnowledgeBase"
      @close="closeDetailDrawer"
    />
  </div>
</template>

<script setup>
/** 功能：承载知识库管理页面的列表展示、详情查看和 CRUD 交互。 */
import { computed, onMounted, ref } from 'vue';
import { Modal, message } from 'ant-design-vue';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue';

import KnowledgeBaseDetailDrawer from '@/components/KnowledgeBaseDetailDrawer.vue';
import KnowledgeBaseFormModal from '@/components/KnowledgeBaseFormModal.vue';
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  fetchKnowledgeBaseDetail,
  fetchKnowledgeBaseList,
  updateKnowledgeBase,
} from '@/services/knowledge-base-service';
import { formatDateTime } from '@/utils/formatters';
import { normalizeErrorMessage } from '@/utils/api';

/** 表格列定义。 */
const columns = [
  { title: '知识库名称', dataIndex: 'name', key: 'name', width: 220 },
  { title: '描述说明', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '所有者', dataIndex: 'owner_id', key: 'owner_id', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: '操作', key: 'actions', width: 200, fixed: 'right' },
];

/** 当前页知识库列表。 */
const items = ref([]);
/** 知识库总数。 */
const total = ref(0);
/** 当前页码。 */
const page = ref(1);
/** 当前分页大小。 */
const pageSize = ref(10);
/** 列表加载状态。 */
const listLoading = ref(false);
/** 详情加载状态。 */
const detailLoading = ref(false);
/** 当前详情对象。 */
const activeKnowledgeBase = ref(null);
/** 表单弹窗开关。 */
const formVisible = ref(false);
/** 详情抽屉开关。 */
const detailVisible = ref(false);
/** 提交中状态。 */
const formSubmitting = ref(false);
/** 当前表单模式。 */
const formMode = ref('create');
/** 当前编辑对象。 */
const editingRecord = ref(null);

/** 分页配置对象。 */
const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条`,
}));

/** 表单回显数据。 */
const formInitialValues = computed(() => ({
  name: editingRecord.value?.name || '',
  description: editingRecord.value?.description || '',
}));

onMounted(async () => {
  try {
    await loadKnowledgeBaseList();
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
});

/**
 * 加载知识库分页列表。
 * @param {{ page?: number, pageSize?: number }} filters 分页参数。
 * @returns {Promise<void>}
 */
async function loadKnowledgeBaseList(filters = {}) {
  listLoading.value = true;

  try {
    /** 当前请求参数。 */
    const params = {
      page: filters.page || page.value,
      pageSize: filters.pageSize || pageSize.value,
    };
    /** 列表响应数据。 */
    const result = await fetchKnowledgeBaseList(params);

    items.value = result.items || [];
    total.value = result.total || 0;
    page.value = Number(result.page) || params.page;
    pageSize.value = Number(result.page_size) || params.pageSize;
  } finally {
    listLoading.value = false;
  }
}

/**
 * 刷新当前列表。
 * @returns {Promise<void>}
 */
async function handleRefresh() {
  try {
    await loadKnowledgeBaseList();
    message.success('知识库列表已刷新');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}

/**
 * 打开创建弹窗。
 * @returns {void}
 */
function openCreateModal() {
  formMode.value = 'create';
  editingRecord.value = null;
  formVisible.value = true;
}

/**
 * 打开编辑弹窗。
 * @param {any} record 当前知识库记录。
 * @returns {void}
 */
function openEditModal(record) {
  formMode.value = 'edit';
  editingRecord.value = record;
  formVisible.value = true;
}

/**
 * 关闭表单弹窗。
 * @returns {void}
 */
function closeFormModal() {
  formVisible.value = false;
}

/**
 * 打开详情抽屉。
 * @param {any} record 当前知识库记录。
 * @returns {Promise<void>}
 */
async function openDetailDrawer(record) {
  detailVisible.value = true;
  detailLoading.value = true;

  try {
    activeKnowledgeBase.value = await fetchKnowledgeBaseDetail(record.id);
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
 * 提交知识库表单。
 * @param {{ name: string, description: string }} payload 表单参数。
 * @returns {Promise<void>}
 */
async function handleSubmit(payload) {
  if (!payload.name) {
    message.warning('请填写知识库名称');
    return;
  }

  formSubmitting.value = true;

  try {
    if (formMode.value === 'edit' && editingRecord.value) {
      await updateKnowledgeBase({
        id: editingRecord.value.id,
        ...payload,
      });
      message.success('知识库已更新');
    } else {
      await createKnowledgeBase({
        ...payload,
      });
      message.success('知识库已创建');
    }

    await loadKnowledgeBaseList({
      page: formMode.value === 'edit' ? page.value : 1,
      pageSize: pageSize.value,
    });
    formVisible.value = false;
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    formSubmitting.value = false;
  }
}

/**
 * 删除知识库。
 * @param {any} record 当前知识库记录。
 * @returns {void}
 */
function handleDelete(record) {
  Modal.confirm({
    title: `确定删除“${record.name}”吗？`,
    content: '如果知识库下仍存在文档，后端会阻止删除。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await deleteKnowledgeBase(record.id);
        await loadKnowledgeBaseList();
        if (activeKnowledgeBase.value?.id === record.id) {
          activeKnowledgeBase.value = null;
        }
        message.success('知识库已删除');
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

  /** 目标页码。 */
  const nextPage = Number(pager?.current) || page.value;
  /** 目标分页大小。 */
  const nextPageSize = Number(pager?.pageSize) || pageSize.value;

  // Ant Design Vue 在分页对象更新后可能再次触发 change，若页码未变则跳过，避免死循环请求。
  if (nextPage === page.value && nextPageSize === pageSize.value) {
    return;
  }

  try {
    await loadKnowledgeBaseList({
      page: nextPage,
      pageSize: nextPageSize,
    });
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}
</script>
