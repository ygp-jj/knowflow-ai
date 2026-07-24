/**
 * 功能：维护文档状态值到界面标签文案和颜色的映射关系。
 * 说明：与切片约束文档 v1.1 对齐；向量化完成终态为 embedded（不再使用 indexed）。
 */

/**
 * 文档状态 → Ant Design Tag 颜色与中文文案。
 */
const DOCUMENT_STATUS_META = {
  uploaded: {
    color: 'processing',
    label: '等待处理',
  },
  parsing: {
    color: 'warning',
    label: '解析中...',
  },
  chunking: {
    color: 'geekblue',
    label: '切片中...',
  },
  chunked: {
    color: 'cyan',
    label: '切片完成',
  },
  embedding: {
    color: 'purple',
    label: '向量生成中...',
  },
  /** 向量化完成终态（决策 B，替代历史命名 indexed）。 */
  embedded: {
    color: 'success',
    label: '已完成',
  },
  failed: {
    color: 'error',
    label: '处理失败（可重试）',
  },
};

/**
 * 后台正在执行中的状态集合。
 * 注意：列表页当前不启用定时轮询（决策 A）；此集合仅供按钮禁用等交互判断。
 */
export const DOCUMENT_ACTIVE_POLL_STATUSES = ['parsing', 'chunking', 'embedding'];

/**
 * 广义「处理中」状态（含待处理 uploaded）。
 */
export const DOCUMENT_PENDING_STATUSES = ['uploaded', 'parsing', 'chunking', 'embedding'];

/**
 * 终态集合：切片完成 / 失败 / 向量化完成。
 */
export const DOCUMENT_TERMINAL_STATUSES = ['chunked', 'failed', 'embedded'];

/**
 * 获取文档状态的展示信息（颜色 + 文案）。
 * @param {string} status 文档状态值（如 uploaded / chunked / embedded）。
 * @returns {{ color: string, label: string }} 颜色 token 与中文标签。
 */
export function getDocumentStatusMeta(status) {
  return (
    DOCUMENT_STATUS_META[status] || {
      color: 'default',
      label: status || '未知状态',
    }
  );
}

/**
 * 判断文档是否仍在异步处理链路中（含待处理）。
 * @param {string} status 文档状态值。
 * @returns {boolean} true 表示尚未到达终态。
 */
export function isDocumentPendingStatus(status) {
  return DOCUMENT_PENDING_STATUSES.includes(status);
}

/**
 * 判断文档是否处于后台正在执行的状态（解析/切片/向量化中）。
 * @param {string} status 文档状态值。
 * @returns {boolean} true 表示 Worker 正在处理。
 */
export function isDocumentActivePollStatus(status) {
  return DOCUMENT_ACTIVE_POLL_STATUSES.includes(status);
}
