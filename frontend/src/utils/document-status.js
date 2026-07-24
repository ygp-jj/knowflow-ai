/**
 * 功能：维护文档状态值到界面标签文案和颜色的映射关系。
 */
/** 文档状态映射。 */
const DOCUMENT_STATUS_META = {
  uploaded: {
    color: 'processing',
    label: '待解析',
  },
  parsing: {
    color: 'warning',
    label: '解析中',
  },
  chunking: {
    color: 'geekblue',
    label: '切片中',
  },
  chunked: {
    color: 'cyan',
    label: '已切片',
  },
  embedding: {
    color: 'purple',
    label: '向量化中',
  },
  indexed: {
    color: 'success',
    label: '已入库',
  },
  failed: {
    color: 'error',
    label: '失败',
  },
};

/**
 * 后台正在执行中的状态（应持续轮询）。
 * 不含 uploaded：仅「待解析」时若 Worker 未启动会永久卡住，避免无限请求。
 */
export const DOCUMENT_ACTIVE_POLL_STATUSES = ['parsing', 'chunking', 'embedding'];

/** 广义处理中状态（含待解析），用于展示判断。 */
export const DOCUMENT_PENDING_STATUSES = ['uploaded', 'parsing', 'chunking', 'embedding'];

/** 可停止轮询的终态。 */
export const DOCUMENT_TERMINAL_STATUSES = ['chunked', 'failed', 'indexed'];

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
 * 判断文档是否仍在异步处理中（含待解析）。
 * @param {string} status 文档状态值。
 * @returns {boolean}
 */
export function isDocumentPendingStatus(status) {
  return DOCUMENT_PENDING_STATUSES.includes(status);
}

/**
 * 判断文档是否处于后台正在执行的状态（应持续轮询）。
 * @param {string} status 文档状态值。
 * @returns {boolean}
 */
export function isDocumentActivePollStatus(status) {
  return DOCUMENT_ACTIVE_POLL_STATUSES.includes(status);
}
