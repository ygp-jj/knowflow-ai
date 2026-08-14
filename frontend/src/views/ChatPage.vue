<template>
  <div class="page-shell">
    <section class="page-banner">
      <div>
        <h2 class="page-banner__title">智能问答</h2>
        <p class="page-banner__desc">
          选择知识库后提问，系统将检索已向量化文档并生成答案（完整返回，非流式）。
        </p>
      </div>
    </section>

    <ACard class="panel-card" :bordered="false">
      <div class="chat-form">
        <ASelect
          v-model:value="selectedKnowledgeBaseId"
          allow-clear
          style="min-width: 280px"
          placeholder="选择知识库"
          :loading="optionsLoading"
          :options="knowledgeBaseOptions"
          :field-names="{ label: 'name', value: 'id' }"
        />
        <ATextarea
          v-model:value="question"
          :rows="4"
          :maxlength="2000"
          show-count
          placeholder="输入你的问题，例如：请假需要谁审批？"
        />
        <div class="chat-form__actions">
          <AButton type="primary" :loading="asking" :disabled="!canSubmit" @click="handleAsk">
            提问
          </AButton>
          <AButton :disabled="asking" @click="handleClear">清空</AButton>
        </div>
      </div>
    </ACard>

    <ACard v-if="result" class="panel-card result-card" :bordered="false" title="回答">
      <p class="answer-text">{{ result.answer }}</p>

      <div v-if="result.references?.length" class="refs">
        <h3>引用切片</h3>
        <div v-for="item in result.references" :key="item.chunk_id" class="ref-item">
          <div class="ref-item__meta">
            <ATag>chunk #{{ item.chunk_id }}</ATag>
            <ATag>文档 {{ item.document_id }}</ATag>
            <ATag v-if="item.score != null" color="blue">score {{ Number(item.score).toFixed(3) }}</ATag>
          </div>
          <pre class="ref-item__content">{{ item.content }}</pre>
        </div>
      </div>
      <AEmpty v-else description="本次无引用切片" />
    </ACard>
  </div>
</template>

<script setup>
/** 功能：知识库单次问答页面（选库、提问、展示答案与引用）。 */
import { computed, onMounted, ref } from 'vue';
import { message } from 'ant-design-vue';

import { askQuestion } from '@/services/chat-service';
import { fetchKnowledgeBaseList } from '@/services/knowledge-base-service';
import { DEFAULT_OWNER_ID } from '@/constants/app';
import { normalizeErrorMessage } from '@/utils/api';

/** 知识库选项。 */
const knowledgeBaseOptions = ref([]);
/** 选项加载中。 */
const optionsLoading = ref(false);
/** 当前选中的知识库 ID。 */
const selectedKnowledgeBaseId = ref(null);
/** 问题文本。 */
const question = ref('');
/** 请求中。 */
const asking = ref(false);
/** 最近一次问答结果。 */
const result = ref(null);

/** 是否允许提交。 */
const canSubmit = computed(() => {
  return Boolean(selectedKnowledgeBaseId.value) && Boolean(question.value?.trim()) && !asking.value;
});

onMounted(async () => {
  await loadKnowledgeBases();
});

/**
 * 加载知识库下拉选项。
 * @returns {Promise<void>}
 */
async function loadKnowledgeBases() {
  optionsLoading.value = true;
  try {
    const data = await fetchKnowledgeBaseList({
      page: 1,
      pageSize: 100,
      ownerId: DEFAULT_OWNER_ID,
    });
    knowledgeBaseOptions.value = data.items || [];
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    optionsLoading.value = false;
  }
}

/**
 * 发起问答。
 * @returns {Promise<void>}
 */
async function handleAsk() {
  if (!canSubmit.value) {
    message.warning('请选择知识库并输入问题');
    return;
  }

  asking.value = true;
  try {
    result.value = await askQuestion({
      knowledgeBaseId: selectedKnowledgeBaseId.value,
      question: question.value.trim(),
    });
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    asking.value = false;
  }
}

/**
 * 清空问题与结果。
 * @returns {void}
 */
function handleClear() {
  question.value = '';
  result.value = null;
}
</script>

<style scoped>
.chat-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-form__actions {
  display: flex;
  gap: 12px;
}

.result-card {
  margin-top: 16px;
}

.answer-text {
  margin: 0 0 20px;
  white-space: pre-wrap;
  line-height: 1.7;
  color: #122033;
  font-size: 15px;
}

.refs h3 {
  margin: 0 0 12px;
  font-size: 15px;
}

.ref-item {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.8);
}

.ref-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.ref-item__content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
  color: #334155;
}
</style>
