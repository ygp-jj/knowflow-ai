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
