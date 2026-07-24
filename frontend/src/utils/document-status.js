/**
 * 功能：维护文档状态值到界面标签文案和颜色的映射关系。
 */
/** 文档状态映射（与切片约束文档 v1.1 对齐）。 */
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
 * 后台正在执行中的状态。
 * 列表页当前不轮询；该集合供按钮禁用等交互使用。
 */
export const DOCUMENT_ACTIVE_POLL_STATUSES = ['parsing', 'chunking', 'embedding'];

/** 广义处理中状态（含待处理）。 */
export const DOCUMENT_PENDING_STATUSES = ['uploaded', 'parsing', 'chunking', 'embedding'];

/** 终态集合：切片完成 / 失败 / 向量化完成。 */
export const DOCUMENT_TERMINAL_STATUSES = ['chunked', 'failed', 'embedded'];

/**
 * 获取文档状态展示信息。
 * @param {string} status 文档状态值。
 * @returns {{ color: string, label: string }}
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
 * 判断文档是否仍在异步处理中（含待处理）。
 * @param {string} status 文档状态值。
 * @returns {boolean}
 */
export function isDocumentPendingStatus(status) {
  return DOCUMENT_PENDING_STATUSES.includes(status);
}

/**
 * 判断文档是否处于后台正在执行的状态。
 * @param {string} status 文档状态值。
 * @returns {boolean}
 */
export function isDocumentActivePollStatus(status) {
  return DOCUMENT_ACTIVE_POLL_STATUSES.includes(status);
}
