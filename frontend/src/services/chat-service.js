/**
 * 功能：封装智能问答相关接口。
 * - askQuestion：一次性拿完整答案（调试/兜底）
 * - askQuestionStream：SSE 流式拿答案（页面默认使用，打字机效果）
 */
import httpClient from './http';
import { resolveApiBaseUrl, unwrapApiResponse } from '@/utils/api';

/**
 * 对知识库发起单次问答（非流式，等全部生成完再返回）。
 * @param {{ knowledgeBaseId: number, question: string }} payload 请求参数。
 * @returns {Promise<{ answer: string, question: string, knowledge_base_id: number, references: any[] }>}
 */
export async function askQuestion(payload) {
  /** 问答响应对象。 */
  const response = await httpClient.post('/chat/ask', {
    knowledge_base_id: payload.knowledgeBaseId,
    question: payload.question,
  });

  return unwrapApiResponse(response.data);
}

/**
 * 解析浏览器读到的 SSE 文本缓冲，拆成一条条事件。
 * SSE 格式大致是：
 *   event: token
 *   data: {"text":"你"}
 *   （空行表示一条事件结束）
 *
 * @param {string} buffer 尚未处理完的文本缓冲。
 * @returns {{ events: Array<{ event: string, data: any }>, rest: string }}
 *          events=已解析出的事件；rest=不完整、留给下次拼接的尾巴。
 */
function parseSseBuffer(buffer) {
  /** 已完整解析的事件列表。 */
  const events = [];
  /** 按「空行」切分事件块；最后一块可能还不完整。 */
  const parts = buffer.split('\n\n');
  /** 最后一块先留着，可能还没收齐。 */
  const rest = parts.pop() || '';

  parts.forEach((block) => {
    const lines = block.split('\n');
    /** 事件名，默认 message。 */
    let eventName = 'message';
    /** data 行拼起来的 JSON 文本。 */
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

    /** 后端约定 data 是一段 JSON。 */
    const raw = dataLines.join('\n');
    try {
      events.push({
        event: eventName,
        data: JSON.parse(raw),
      });
    } catch (error) {
      // 解析失败时把原始字符串塞进去，方便排查，页面侧再兜底
      events.push({
        event: eventName,
        data: { message: raw },
      });
    }
  });

  return { events, rest };
}

/**
 * 对知识库发起流式问答（SSE）。
 * 后端会陆续推：
 *   1) references —— 引用切片列表（可先展示）
 *   2) token —— 答案增量文字（拼起来就是完整答案）
 *   3) done —— 正常结束
 *   或 error —— 失败
 *
 * @param {{ knowledgeBaseId: number, question: string }} payload 请求参数。
 * @param {{
 *   onReferences?: (refs: any[]) => void,
 *   onToken?: (text: string) => void,
 *   onDone?: () => void,
 *   onError?: (message: string) => void,
 *   signal?: AbortSignal,
 * }} handlers 回调；页面用它们更新界面。
 * @returns {Promise<void>}
 */
export async function askQuestionStream(payload, handlers = {}) {
  /** API 根路径，例如 /api/v1。 */
  const baseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
  /** 完整流式地址。 */
  const url = `${baseUrl}/chat/ask-stream`;

  /** 发起 POST；流式不能用 axios 方便消费，所以用原生 fetch。 */
  const response = await fetch(url, {
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

  if (!response.ok) {
    throw new Error(`流式问答请求失败（HTTP ${response.status}）`);
  }
  if (!response.body) {
    throw new Error('浏览器未返回可读数据流');
  }

  /** 按块读取响应体。 */
  const reader = response.body.getReader();
  /** 把二进制块解码成文字。 */
  const decoder = new TextDecoder('utf-8');
  /** 拼不完整的 SSE 片段。 */
  let buffer = '';
  /** 是否已经结束（done 或 error），避免重复回调。 */
  let settled = false;

  /**
   * 安全触发结束回调（只触发一次）。
   * @returns {void}
   */
  function settleDone() {
    if (settled) {
      return;
    }
    settled = true;
    handlers.onDone?.();
  }

  /**
   * 安全触发错误回调（只触发一次）。
   * @param {string} errMessage 错误文案。
   * @returns {void}
   */
  function settleError(errMessage) {
    if (settled) {
      return;
    }
    settled = true;
    handlers.onError?.(errMessage);
  }

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

  // 流读完但服务端没发 done / error 时，视为正常结束
  settleDone();
}
