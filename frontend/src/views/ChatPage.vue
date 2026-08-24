<template>
  <!--
    5B 智能问答页：左侧会话列表 + 右侧消息流。
    流程：新建会话(选库) → 提问(ask-stream) → 可停止 → 刷新仍能看到历史。
  -->
  <div class="page-shell chat-page">
    <section class="page-banner">
      <div>
        <h2 class="page-banner__title">智能问答</h2>
        <p class="page-banner__desc">
          左侧管理会话，右侧多轮追问；答案流式输出。会话创建时绑定知识库，之后不可更换。
        </p>
      </div>
    </section>

    <div class="chat-layout">
      <!-- ========== 左侧：会话列表 ========== -->
      <ACard class="panel-card session-panel" :bordered="false" title="会话">
        <div class="session-panel__toolbar">
          <ASelect
            v-model:value="createKnowledgeBaseId"
            allow-clear
            style="flex: 1; min-width: 0"
            placeholder="新建时选择知识库"
            :loading="optionsLoading"
            :options="knowledgeBaseOptions"
            :field-names="{ label: 'name', value: 'id' }"
          />
          <AButton type="primary" :loading="creatingSession" @click="handleCreateSession">
            新建
          </AButton>
        </div>

        <ASpin :spinning="sessionsLoading">
          <div v-if="sessions.length" class="session-list">
            <div
              v-for="item in sessions"
              :key="item.id"
              class="session-item"
              :class="{ 'session-item--active': item.id === activeSessionId }"
              @click="handleSelectSession(item)"
            >
              <div class="session-item__main">
                <!-- 双击标题进入编辑；单击选中会话 -->
                <template v-if="editingSessionId === item.id">
                  <AInput
                    v-model:value="editingTitle"
                    size="small"
                    @click.stop
                    @pressEnter="handleSaveTitle(item)"
                  />
                  <AButton size="small" type="link" @click.stop="handleSaveTitle(item)">保存</AButton>
                </template>
                <template v-else>
                  <div class="session-item__title" @dblclick.stop="startEditTitle(item)">
                    {{ item.title }}
                  </div>
                  <div class="session-item__meta">
                    {{ item.knowledge_base_name || `知识库 #${item.knowledge_base_id}` }}
                  </div>
                </template>
              </div>
              <div class="session-item__actions" @click.stop>
                <AButton type="link" size="small" @click="startEditTitle(item)">改名</AButton>
                <AButton type="link" size="small" danger @click="handleDeleteSession(item)">
                  删除
                </AButton>
              </div>
            </div>
          </div>
          <AEmpty v-else description="暂无会话，请先新建" />
        </ASpin>
      </ACard>

      <!-- ========== 右侧：消息区 ========== -->
      <ACard class="panel-card message-panel" :bordered="false">
        <template #title>
          <div class="message-panel__title">
            <span>{{ activeSession?.title || '请选择或新建会话' }}</span>
            <ATag v-if="activeSession">{{ activeSession.knowledge_base_name || `KB #${activeSession.knowledge_base_id}` }}</ATag>
          </div>
        </template>

        <div v-if="!activeSessionId" class="message-empty">
          <AEmpty description="请在左侧新建或选择一个会话后再提问" />
        </div>

        <template v-else>
          <div ref="messageListRef" class="message-list">
            <div
              v-for="(msg, index) in displayMessages"
              :key="msg.localKey || msg.id || index"
              class="message-bubble"
              :class="msg.role === 'user' ? 'message-bubble--user' : 'message-bubble--assistant'"
            >
              <div class="message-bubble__role">{{ msg.role === 'user' ? '我' : '助手' }}</div>
              <!-- 用户消息：纯文本；助手消息：渲染 Markdown（加粗、列表等） -->
              <div
                v-if="msg.role === 'assistant'"
                class="message-bubble__content message-bubble__content--md"
                v-html="renderAssistantHtml(msg)"
              />
              <div v-else class="message-bubble__content">{{ msg.content }}</div>
              <span v-if="msg.streaming" class="answer-cursor">▍</span>
              <!--
                引用区：仅在本轮 done 后展示（streaming=false）。
                默认收起，点击「引用 (N)」展开完整正文。
              -->
              <div
                v-if="msg.role === 'assistant' && !msg.streaming && msg.references?.length"
                class="message-refs"
              >
                <button type="button" class="message-refs__toggle" @click="toggleMessageRefs(msg)">
                  引用 ({{ msg.references.length }})
                  <span class="message-refs__toggle-hint">{{ msg.refsExpanded ? '收起' : '展开' }}</span>
                </button>
                <div v-show="msg.refsExpanded" class="message-refs__body">
                  <div
                    v-for="refItem in msg.references"
                    :key="refItem.chunk_id || refItem.id"
                    class="ref-item"
                  >
                    <div class="ref-item__meta">
                      <ATag>chunk #{{ refItem.chunk_id }}</ATag>
                      <ATag>文档 {{ refItem.document_id }}</ATag>
                      <ATag v-if="refItem.score != null" color="blue">
                        score {{ Number(refItem.score).toFixed(3) }}
                      </ATag>
                    </div>
                    <pre class="ref-item__content">{{ refItem.content || refItem.content_preview }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="composer">
            <ATextarea
              v-model:value="question"
              :rows="3"
              :maxlength="2000"
              show-count
              :disabled="asking"
              placeholder="输入追问，例如：那病假工资怎么算？"
              @keydown.enter.exact.prevent="handleAskFromEnter"
            />
            <div class="composer__actions">
              <AButton
                v-if="asking"
                danger
                @click="handleStop"
              >
                停止生成
              </AButton>
              <AButton type="primary" :loading="asking" :disabled="!canSubmit" @click="handleAsk">
                发送
              </AButton>
            </div>
          </div>
        </template>
      </ACard>
    </div>
  </div>
</template>

<script setup>
/**
 * 功能：多轮会话问答页（5B）。
 *
 * 交接要点：
 * 1. 身份由 JWT Bearer 决定，前端不再传 userId
 * 2. 提问只调 askSessionStream；停止 = AbortController.abort()，后端不落半截 assistant
 * 3. 停止后本地去掉 streaming 助手气泡；刷新 messages/list 应只见已落库的 user
 * 4. 双击或点「改名」可改 title；首问后端会把「新会话」自动改成问题截断
 * 5. 引用默认收起；仅流式 done 后显示「引用 (N)」，展开见完整正文
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { message, Modal } from 'ant-design-vue';

import {
  askSessionStream,
  createSession,
  deleteSession,
  fetchMessageList,
  fetchSessionList,
  updateSessionTitle,
} from '@/services/chat-service';
import { fetchKnowledgeBaseList } from '@/services/knowledge-base-service';
import { normalizeErrorMessage } from '@/utils/api';
import { renderMarkdown } from '@/utils/markdown';

/** 后端创建会话时的默认标题；首问后本地同步改名用。 */
const DEFAULT_SESSION_TITLE = '新会话';
/** 与后端 SESSION_TITLE_MAX_LEN 一致。 */
const SESSION_TITLE_MAX_LEN = 50;

/** 知识库下拉。 */
const knowledgeBaseOptions = ref([]);
const optionsLoading = ref(false);
/** 新建会话时选中的知识库。 */
const createKnowledgeBaseId = ref(null);
const creatingSession = ref(false);

/** 会话列表。 */
const sessions = ref([]);
const sessionsLoading = ref(false);
/** 当前选中的会话 ID。 */
const activeSessionId = ref(null);
/** 改名中的会话。 */
const editingSessionId = ref(null);
const editingTitle = ref('');

/** 右侧消息（含本地临时 streaming 气泡）。 */
const displayMessages = ref([]);
const messagesLoading = ref(false);
const messageListRef = ref(null);

/** 输入框与流式状态。 */
const question = ref('');
const asking = ref(false);
/** 取消进行中的流式请求。 */
let abortController = null;
/** 本地临时助手气泡下标，停止时可删掉。 */
let streamingAssistantIndex = -1;

/** 当前选中会话对象。 */
const activeSession = computed(() => {
  return sessions.value.find((item) => item.id === activeSessionId.value) || null;
});

/** 是否可发送。 */
const canSubmit = computed(() => {
  return Boolean(activeSessionId.value) && Boolean(question.value?.trim()) && !asking.value;
});

onMounted(async () => {
  await Promise.all([loadKnowledgeBases(), loadSessions()]);
});

onBeforeUnmount(() => {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
});

/**
 * 加载知识库下拉。
 * @returns {Promise<void>}
 */
async function loadKnowledgeBases() {
  optionsLoading.value = true;
  try {
    const data = await fetchKnowledgeBaseList({
      page: 1,
      pageSize: 100,
    });
    knowledgeBaseOptions.value = data.items || [];
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    optionsLoading.value = false;
  }
}

/**
 * 刷新左侧会话列表。
 * @returns {Promise<void>}
 */
async function loadSessions() {
  sessionsLoading.value = true;
  try {
    const data = await fetchSessionList({ page: 1, pageSize: 50 });
    sessions.value = data.items || [];
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    sessionsLoading.value = false;
  }
}

/**
 * 新建会话。
 * @returns {Promise<void>}
 */
async function handleCreateSession() {
  if (!createKnowledgeBaseId.value) {
    message.warning('请先选择知识库');
    return;
  }
  creatingSession.value = true;
  try {
    const session = await createSession({
      knowledgeBaseId: createKnowledgeBaseId.value,
    });
    await loadSessions();
    activeSessionId.value = session.id;
    displayMessages.value = [];
    message.success('会话已创建');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    creatingSession.value = false;
  }
}

/**
 * 选中会话并拉取消息。
 * @param {any} item 会话。
 * @returns {Promise<void>}
 */
async function handleSelectSession(item) {
  if (asking.value) {
    message.warning('请先停止当前生成再切换会话');
    return;
  }
  activeSessionId.value = item.id;
  await loadMessages(item.id);
}

/**
 * 拉取某会话历史消息。
 * @param {number} sessionId 会话 ID。
 * @returns {Promise<void>}
 */
async function loadMessages(sessionId) {
  messagesLoading.value = true;
  try {
    const data = await fetchMessageList({
      sessionId,
      page: 1,
      pageSize: 200,
    });
    displayMessages.value = (data.items || []).map((msg) => mapMessageForDisplay(msg));
    await scrollToBottom();
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  } finally {
    messagesLoading.value = false;
  }
}

/**
 * 开始编辑标题。
 * @param {any} item 会话。
 * @returns {void}
 */
function startEditTitle(item) {
  editingSessionId.value = item.id;
  editingTitle.value = item.title || '';
}

/**
 * 保存标题。
 * @param {any} item 会话。
 * @returns {Promise<void>}
 */
async function handleSaveTitle(item) {
  const title = (editingTitle.value || '').trim();
  if (!title) {
    message.warning('标题不能为空');
    return;
  }
  try {
    await updateSessionTitle({ id: item.id, title });
    editingSessionId.value = null;
    patchSessionTitleLocal(item.id, title);
    message.success('标题已更新');
  } catch (error) {
    message.error(normalizeErrorMessage(error));
  }
}

/**
 * 删除会话。
 * @param {any} item 会话。
 * @returns {void}
 */
function handleDeleteSession(item) {
  Modal.confirm({
    title: '删除会话？',
    content: '将同时删除该会话下的消息与引用，且不可恢复。',
    okType: 'danger',
    async onOk() {
      try {
        await deleteSession(item.id);
        if (activeSessionId.value === item.id) {
          activeSessionId.value = null;
          displayMessages.value = [];
        }
        await loadSessions();
        message.success('已删除');
      } catch (error) {
        message.error(normalizeErrorMessage(error));
      }
    },
  });
}

/**
 * 统一消息展示结构（历史 / 本地气泡共用）。
 * @param {any} msg 原始消息。
 * @param {{ streaming?: boolean, localKey?: string }} [extra] 额外字段。
 * @returns {any}
 */
function mapMessageForDisplay(msg, extra = {}) {
  return {
    ...msg,
    ...extra,
    references: (msg.references || []).map((ref) => ({
      ...ref,
      content: ref.content_preview || ref.content,
      chunk_id: ref.chunk_id,
    })),
    /** 引用折叠：默认收起。 */
    refsExpanded: false,
    streaming: extra.streaming ?? false,
  };
}

/**
 * 切换某条助手消息的引用展开/收起。
 * @param {any} msg 消息对象。
 * @returns {void}
 */
function toggleMessageRefs(msg) {
  msg.refsExpanded = !msg.refsExpanded;
}

/**
 * 助手气泡：把 Markdown 转成 HTML 展示。
 * @param {{ content?: string, streaming?: boolean }} msg 消息对象。
 * @returns {string}
 */
function renderAssistantHtml(msg) {
  return renderMarkdown(msg?.content || '');
}

/**
 * 本地更新左侧某条会话标题，避免每次提问都请求 sessions/list。
 * @param {number} sessionId 会话 ID。
 * @param {string} title 新标题。
 * @returns {void}
 */
function patchSessionTitleLocal(sessionId, title) {
  const index = sessions.value.findIndex((item) => item.id === sessionId);
  if (index < 0) {
    return;
  }
  sessions.value[index] = {
    ...sessions.value[index],
    title,
  };
}

/**
 * 首问后：若仍是默认「新会话」，本地把标题改成问题截断（与后端逻辑一致）。
 * @param {string} questionText 用户问题。
 * @returns {void}
 */
function maybePatchSessionTitleAfterAsk(questionText) {
  const session = sessions.value.find((item) => item.id === activeSessionId.value);
  if (!session || session.title !== DEFAULT_SESSION_TITLE) {
    return;
  }
  const cleaned = (questionText || '').trim().replace(/\n/g, ' ');
  let title = cleaned;
  if (title.length > SESSION_TITLE_MAX_LEN) {
    title = `${title.slice(0, SESSION_TITLE_MAX_LEN)}…`;
  }
  patchSessionTitleLocal(activeSessionId.value, title);
}

/**
 * Enter 发送（Shift+Enter 仍换行，由 textarea 默认行为处理）。
 * @returns {void}
 */
function handleAskFromEnter() {
  handleAsk();
}

/**
 * 发起会话内流式提问。
 * @returns {Promise<void>}
 */
async function handleAsk() {
  if (!canSubmit.value) {
    message.warning('请选择会话并输入问题');
    return;
  }

  if (abortController) {
    abortController.abort();
  }
  abortController = new AbortController();

  const text = question.value.trim();
  if (!text) {
    message.warning('请输入问题');
    return;
  }
  // 立刻清空输入框，避免发送后仍显示上一句（Enter / 按钮共用）
  question.value = '';

  // 本地先插入用户气泡（与后端落库一致；刷新后仍在）
  displayMessages.value.push(
    mapMessageForDisplay(
      { role: 'user', content: text, references: [] },
      { localKey: `u-${Date.now()}` },
    ),
  );

  displayMessages.value.push(
    mapMessageForDisplay(
      { role: 'assistant', content: '', references: [] },
      { localKey: `a-${Date.now()}`, streaming: true },
    ),
  );
  streamingAssistantIndex = displayMessages.value.length - 1;
  asking.value = true;
  await scrollToBottom();

  let finished = false;
  /** 本轮流式过程中收到的引用，结束后写到助手气泡上。 */
  let pendingRefs = [];

  try {
    await askSessionStream(
      {
        sessionId: activeSessionId.value,
        question: text,
      },
      {
        signal: abortController.signal,
        onReferences(refs) {
          pendingRefs = refs || [];
          if (streamingAssistantIndex >= 0 && displayMessages.value[streamingAssistantIndex]) {
            displayMessages.value[streamingAssistantIndex].references = pendingRefs.map((ref) => ({
              ...ref,
              content: ref.content || ref.content_preview,
            }));
          }
        },
        onToken(token) {
          if (streamingAssistantIndex >= 0 && displayMessages.value[streamingAssistantIndex]) {
            displayMessages.value[streamingAssistantIndex].content += token || '';
            scrollToBottom();
          }
        },
        onDone() {
          if (finished) {
            return;
          }
          finished = true;
          if (streamingAssistantIndex >= 0 && displayMessages.value[streamingAssistantIndex]) {
            displayMessages.value[streamingAssistantIndex].streaming = false;
          }
          streamingAssistantIndex = -1;
          asking.value = false;
          // 首问自动改名：只改本地 sessions，不刷 list 接口
          maybePatchSessionTitleAfterAsk(text);
        },
        onError(errMessage) {
          if (finished) {
            return;
          }
          finished = true;
          removeStreamingAssistant();
          asking.value = false;
          message.error(errMessage || '流式问答失败');
        },
      },
    );
  } catch (error) {
    if (error?.name === 'AbortError') {
      // 用户点了停止：去掉半截助手气泡，用户气泡保留
      removeStreamingAssistant();
      asking.value = false;
      return;
    }
    removeStreamingAssistant();
    message.error(normalizeErrorMessage(error));
  } finally {
    asking.value = false;
    abortController = null;
    if (streamingAssistantIndex >= 0 && displayMessages.value[streamingAssistantIndex]) {
      displayMessages.value[streamingAssistantIndex].streaming = false;
    }
    streamingAssistantIndex = -1;
  }
}

/**
 * 停止生成：中断 fetch；不落 assistant（后端约定）。
 * @returns {void}
 */
function handleStop() {
  if (abortController) {
    abortController.abort();
  }
}

/**
 * 去掉本地 streaming 助手气泡。
 * @returns {void}
 */
function removeStreamingAssistant() {
  if (streamingAssistantIndex >= 0) {
    displayMessages.value.splice(streamingAssistantIndex, 1);
    streamingAssistantIndex = -1;
  } else {
    // 兜底：删掉最后一个 streaming 标记的助手消息
    const idx = displayMessages.value.findIndex((m) => m.streaming && m.role === 'assistant');
    if (idx >= 0) {
      displayMessages.value.splice(idx, 1);
    }
  }
}

/**
 * 消息区滚到底部。
 * @returns {Promise<void>}
 */
async function scrollToBottom() {
  await nextTick();
  const el = messageListRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}
</script>

<style scoped>
.chat-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  align-items: stretch;
  min-height: 640px;
}

.session-panel,
.message-panel {
  display: flex;
  flex-direction: column;
  min-height: 640px;
}

.session-panel__toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 560px;
  overflow: auto;
}

.session-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  cursor: pointer;
  background: #fff;
}

.session-item--active {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.06);
}

.session-item__title {
  font-weight: 600;
  color: #122033;
  word-break: break-word;
}

.session-item__meta {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.session-item__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.message-panel__title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.message-empty {
  padding: 48px 0;
}

.message-list {
  flex: 1;
  max-height: 480px;
  overflow: auto;
  padding: 8px 4px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 12px;
}

.message-bubble--user {
  align-self: flex-end;
  background: rgba(37, 99, 235, 0.1);
}

.message-bubble--assistant {
  align-self: flex-start;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.message-bubble__role {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.message-bubble__content {
  white-space: pre-wrap;
  line-height: 1.7;
  color: #122033;
}

/* 助手 Markdown 区域：列表、加粗等由 marked 生成 HTML */
.message-bubble__content--md {
  white-space: normal;
}

.message-bubble__content--md :deep(p) {
  margin: 0 0 0.6em;
}

.message-bubble__content--md :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble__content--md :deep(ol),
.message-bubble__content--md :deep(ul) {
  margin: 0.4em 0 0.6em 1.2em;
  padding: 0;
}

.message-bubble__content--md :deep(li) {
  margin-bottom: 0.35em;
}

.message-bubble__content--md :deep(strong) {
  font-weight: 600;
  color: #0f172a;
}

.answer-cursor {
  display: inline-block;
  margin-left: 4px;
  vertical-align: baseline;
  color: #2563eb;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.message-refs {
  margin-top: 10px;
}

.message-refs__toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  background: #fff;
  color: #334155;
  font-size: 13px;
  cursor: pointer;
}

.message-refs__toggle:hover {
  border-color: #2563eb;
  color: #2563eb;
}

.message-refs__toggle-hint {
  font-size: 12px;
  color: #64748b;
}

.message-refs__body {
  margin-top: 8px;
}

.ref-item {
  margin-bottom: 8px;
  padding: 8px 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #fff;
}

.ref-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.ref-item__content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 12px;
  color: #334155;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  padding-top: 12px;
}

.composer__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 960px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }
}
</style>
