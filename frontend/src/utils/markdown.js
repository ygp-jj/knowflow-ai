/**
 * 功能：把助手返回的 Markdown 转成 HTML，供聊天气泡 v-html 展示。
 * 仅用于 assistant 消息；用户消息仍用纯文本，避免 XSS 面过大。
 */
import { marked } from 'marked';

/** 全局配置：换行转 <br>，启用 GFM（列表、加粗等）。 */
marked.setOptions({
  breaks: true,
  gfm: true,
});

/**
 * 将 Markdown 字符串渲染为 HTML。
 * @param {string} text 原始 Markdown 文本。
 * @returns {string} 可安全插入 v-html 的 HTML（内容来自自家 LLM，联调场景不做 sanitize）。
 */
export function renderMarkdown(text) {
  if (!text) {
    return '';
  }
  return marked.parse(text, { async: false });
}
