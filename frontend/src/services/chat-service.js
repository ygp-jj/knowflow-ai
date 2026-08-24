/**
 * 功能：智能问答相关接口（无会话调试 + 5B 多轮会话）。
 *
 * 交接说明：
 * - 产品页默认走「会话」：createSession / listSessions / askSessionStream
 * - askQuestion / askQuestionStream 仍保留，给脚本或联调无会话场景用
 * - SSE 解析逻辑共用 parseSseBuffer，事件名：references / token / done / error
 */
import httpClient from './http';
import { resolveApiBaseUrl, unwrapApiResponse } from '@/utils/api';

/**
 * 对知识库发起单次问答（无会话、非流式）。
 * @param {{ knowledgeBaseId: number, question: string }} payload 请求参数。
 * @returns {Promise<{ answer: string, question: string, knowledge_base_id: number, references: any[] }>}
 */
export async function askQuestion(payload) {
  const response = await httpClient.post('/chat/ask', {
    knowledge_base_id: payload.knowledgeBaseId,
    question: payload.question,
  });
  return unwrapApiResponse(response.data);
}

/**
 * 解析浏览器读到的 SSE 文本缓冲，拆成一条条事件。
 * @param {string} buffer 尚未处理完的文本缓冲。
 * @returns {{ events: Array<{ event: string, data: any }>, rest: string }}
 */
function parseSseBuffer(buffer) {
  const events = [];
  const parts = buffer.split('\n\n');
  const rest = parts.pop() || '';

  parts.forEach((block) => {
    const lines = block.split('\n');
    let eventName = 'message';
    const dataLines = [];

    lines.forEach((line) => {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    });

    if (!dataLines.length) {
      return;
    }

    const raw = dataLines.join('\n');
    try {
      events.push({ event: eventName, data: JSON.parse(raw) });
    } catch (error) {
      events.push({ event: eventName, data: { message: raw } });
    }
  });

  return { events, rest };
}

/**
 * 消费 SSE 响应体，按事件回调。
 * @param {Response} response fetch 响应。
 * @param {{
 *   onReferences?: (refs: any[]) => void,
 *   onToken?: (text: string) => void,
 *   onDone?: () => void,
 *   onError?: (message: string) => void,
 * }} handlers 回调。
 * @returns {Promise<void>}
 */
async function consumeSseResponse(response, handlers = {}) {
  if (!response.ok) {
    throw new Error(`流式请求失败（HTTP ${response.status}）`);
  }
  if (!response.body) {
    throw new Error('浏览器未返回可读数据流');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let settled = false;

  function settleDone() {
    if (settled) {
      return;
    }
    settled = true;
    handlers.onDone?.();
  }

  function settleError(errMessage) {
    if (settled) {
      return;
    }
    settled = true;
    handlers.onError?.(errMessage);
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const parsed = parseSseBuffer(buffer);
      buffer = parsed.rest;

      parsed.events.forEach((item) => {
        if (item.event === 'references') {
          handlers.onReferences?.(item.data?.references || []);
        } else if (item.event === 'token') {
          handlers.onToken?.(item.data?.text || '');
        } else if (item.event === 'done') {
          settleDone();
        } else if (item.event === 'error') {
          settleError(item.data?.message || '流式问答失败');
        }
      });
    }

    settleDone();
  } catch (error) {
    // 用户点击停止时 fetch/reader 会抛 AbortError，不应触发 onDone
    if (error?.name === 'AbortError') {
      return;
    }
    throw error;
  }
}

/**
 * 无会话流式问答（5A）。
 * @param {{ knowledgeBaseId: number, question: string }} payload 请求参数。
 * @param {object} handlers 回调（含可选 signal）。
 * @returns {Promise<void>}
 */
export async function askQuestionStream(payload, handlers = {}) {
  const baseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
  const response = await fetch(`${baseUrl}/chat/ask-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      knowledge_base_id: payload.knowledgeBaseId,
      question: payload.question,
    }),
    signal: handlers.signal,
  });
  await consumeSseResponse(response, handlers);
}

/**
 * 创建会话（绑定知识库；缺省标题「新会话」）。
 * @param {{ userId: number, knowledgeBaseId: number, title?: string }} payload 参数。
 * @returns {Promise<any>}
 */
export async function createSession(payload) {
  const body = {
    user_id: payload.userId,
    knowledge_base_id: payload.knowledgeBaseId,
  };
  if (payload.title) {
    body.title = payload.title;
  }
  const response = await httpClient.post('/chat/sessions/create', body);
  return unwrapApiResponse(response.data);
}

/**
 * 分页列出会话。
 * @param {{ userId: number, page?: number, pageSize?: number }} filters 条件。
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
export async function fetchSessionList(filters) {
  const response = await httpClient.get('/chat/sessions/list', {
    params: {
      user_id: filters.userId,
      page: filters.page || 1,
      page_size: filters.pageSize || 50,
    },
  });
  return unwrapApiResponse(response.data);
}

/**
 * 会话详情。
 * @param {number} id 会话 ID。
 * @param {number} userId 用户 ID。
 * @returns {Promise<any>}
 */
export async function fetchSessionDetail(id, userId) {
  const response = await httpClient.get('/chat/sessions/detail', {
    params: { id, user_id: userId },
  });
  return unwrapApiResponse(response.data);
}

/**
 * 手动改会话标题。
 * @param {{ id: number, userId: number, title: string }} payload 参数。
 * @returns {Promise<any>}
 */
export async function updateSessionTitle(payload) {
  const response = await httpClient.put('/chat/sessions/update', {
    id: payload.id,
    user_id: payload.userId,
    title: payload.title,
  });
  return unwrapApiResponse(response.data);
}

/**
 * 删除会话（级联消息与引用）。
 * @param {number} id 会话 ID。
 * @param {number} userId 用户 ID。
 * @returns {Promise<null>}
 */
export async function deleteSession(id, userId) {
  const response = await httpClient.delete('/chat/sessions/delete', {
    params: { id, user_id: userId },
  });
  return unwrapApiResponse(response.data);
}

/**
 * 拉取会话消息列表（含 assistant.references）。
 * @param {{ sessionId: number, userId: number, page?: number, pageSize?: number }} filters 条件。
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
export async function fetchMessageList(filters) {
  const response = await httpClient.get('/chat/messages/list', {
    params: {
      session_id: filters.sessionId,
      user_id: filters.userId,
      page: filters.page || 1,
      page_size: filters.pageSize || 100,
    },
  });
  return unwrapApiResponse(response.data);
}

/**
 * 会话内流式提问（5B 产品主路径）。
 * @param {{ sessionId: number, userId: number, question: string }} payload 参数。
 * @param {object} handlers 回调（onReferences / onToken / onDone / onError / signal）。
 * @returns {Promise<void>}
 */
export async function askSessionStream(payload, handlers = {}) {
  const baseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
  const response = await fetch(`${baseUrl}/chat/sessions/ask-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      session_id: payload.sessionId,
      user_id: payload.userId,
      question: payload.question,
    }),
    signal: handlers.signal,
  });
  await consumeSseResponse(response, handlers);
}
