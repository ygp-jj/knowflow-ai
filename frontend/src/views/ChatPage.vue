<template>
  <div class="page-shell">
    <section class="page-banner">
      <div>
        <h2 class="page-banner__title">智能问答</h2>
        <p class="page-banner__desc">
          选择知识库后提问：先检索已向量化文档，再流式生成答案（边出字边显示）。仅检索状态为「已完成」的文档。
        </p>
      </div>
    </section>

    <ACard class="panel-card" :bordered="false">
      <div class="chat-form">
        <!-- 知识库下拉：决定去哪个库里做向量检索 -->
        <ASelect
          v-model:value="selectedKnowledgeBaseId"
          allow-clear
          style="min-width: 280px"
          placeholder="选择知识库"
          :loading="optionsLoading"
          :options="knowledgeBaseOptions"
          :field-names="{ label: 'name', value: 'id' }"
        />
        <!-- 用户问题输入框 -->
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

    <!-- 有结果（或正在流式输出）时展示回答区 -->
    <ACard v-if="showResultPanel" class="panel-card result-card" :bordered="false" title="回答">
      <p class="answer-text">
        {{ streamingAnswer || '正在生成…' }}
        <!-- 流式进行中给一个闪烁光标，方便看出还在输出 -->
        <span v-if="asking" class="answer-cursor">▍</span>
      </p>

      <div v-if="references.length" class="refs">
        <h3>引用切片</h3>
        <div v-for="item in references" :key="item.chunk_id" class="ref-item">
          <div class="ref-item__meta">
            <ATag>chunk #{{ item.chunk_id }}</ATag>
            <ATag>文档 {{ item.document_id }}</ATag>
            <ATag v-if="item.score != null" color="blue">score {{ Number(item.score).toFixed(3) }}</ATag>
          </div>
          <pre class="ref-item__content">{{ item.content }}</pre>
        </div>
      </div>
      <AEmpty v-else-if="!asking" description="本次无引用切片" />
    </ACard>
  </div>
</template>

<script setup>
/**
 * 功能：知识库单次问答页面。
 * 流程（给前端同学看）：
 * 1. 加载知识库下拉选项
 * 2. 用户选库、输入问题，点「提问」
 * 3. 调用 askQuestionStream（SSE）
 *    - onReferences：先展示引用
 *    - onToken：把增量文字拼到答案里（打字机效果）
 *    - onError / 结束：关掉 loading
 */
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import { message } from 'ant-design-vue';

import { askQuestionStream } from '@/services/chat-service';
import { fetchKnowledgeBaseList } from '@/services/knowledge-base-service';
import { DEFAULT_OWNER_ID } from '@/constants/app';
import { normalizeErrorMessage } from '@/utils/api';

/** 知识库下拉选项列表。 */
const knowledgeBaseOptions = ref([]);
/** 下拉是否加载中。 */
const optionsLoading = ref(false);
/** 当前选中的知识库 ID。 */
const selectedKnowledgeBaseId = ref(null);
/** 输入框里的问题原文。 */
const question = ref('');
/** 是否正在请求 / 流式输出中（按钮 loading）。 */
const asking = ref(false);
/** 流式拼起来的完整答案文本。 */
const streamingAnswer = ref('');
/** 本次问答的引用切片列表。 */
const references = ref([]);
/** 是否已经开始展示结果面板（点提问后为 true）。 */
const resultStarted = ref(false);
/** 用于取消进行中的 fetch（例如离开页面）。 */
let abortController = null;

/** 是否允许点击「提问」。 */
const canSubmit = computed(() => {
  return Boolean(selectedKnowledgeBaseId.value) && Boolean(question.value?.trim()) && !asking.value;
});

/** 是否显示下方「回答」卡片。 */
const showResultPanel = computed(() => resultStarted.value);

onMounted(async () => {
  await loadKnowledgeBases();
});

onBeforeUnmount(() => {
  // 离开页面时取消未完成的流式请求，避免回调改到已卸载组件
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
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
 * 发起流式问答。
 * @returns {Promise<void>}
 */
async function handleAsk() {
  if (!canSubmit.value) {
    message.warning('请选择知识库并输入问题');
    return;
  }

  // 取消上一次未完成的请求
  if (abortController) {
    abortController.abort();
  }
  abortController = new AbortController();

  // 重置展示区，准备接收新一轮流式内容
  resultStarted.value = true;
  streamingAnswer.value = '';
  references.value = [];
  asking.value = true;

  /** 流是否已经正常/异常结束（防止 onDone 重复关 loading）。 */
  let finished = false;

  try {
    await askQuestionStream(
      {
        knowledgeBaseId: selectedKnowledgeBaseId.value,
        question: question.value.trim(),
      },
      {
        signal: abortController.signal,
        // 后端先推引用：页面可以一边出字一边看用来源
        onReferences(refs) {
          references.value = refs || [];
        },
        // 每个 token 是一小段字，拼到答案末尾
        onToken(text) {
          streamingAnswer.value += text || '';
        },
        onDone() {
          if (finished) {
            return;
          }
          finished = true;
          asking.value = false;
        },
        onError(errMessage) {
          if (finished) {
            return;
          }
          finished = true;
          asking.value = false;
          message.error(errMessage || '流式问答失败');
        },
      },
    );
  } catch (error) {
    // 用户主动取消（离开页面）不弹错误
    if (error?.name === 'AbortError') {
      return;
    }
    message.error(normalizeErrorMessage(error));
  } finally {
    asking.value = false;
    abortController = null;
  }
}

/**
 * 清空问题与结果区。
 * @returns {void}
 */
function handleClear() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  question.value = '';
  streamingAnswer.value = '';
  references.value = [];
  resultStarted.value = false;
  asking.value = false;
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

.answer-cursor {
  display: inline-block;
  margin-left: 2px;
  color: #2563eb;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
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
