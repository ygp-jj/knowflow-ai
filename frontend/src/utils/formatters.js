/**
 * 功能：提供文件大小和日期时间等管理台展示格式化工具。
 */
/** 文件大小单位列表。 */
const FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB'];

/**
 * 格式化文件大小。
 * @param {number} fileSize 文件字节数。
 * @returns {string}
 */
export function formatFileSize(fileSize) {
  if (!Number.isFinite(fileSize) || fileSize < 0) {
    return '--';
  }

  if (fileSize < 1024) {
    return `${fileSize} B`;
  }

  /** 当前换算值。 */
  let displayValue = fileSize;
  /** 当前单位索引。 */
  let unitIndex = 0;

  while (displayValue >= 1024 && unitIndex < FILE_SIZE_UNITS.length - 1) {
    displayValue /= 1024;
    unitIndex += 1;
  }

  return `${displayValue.toFixed(1)} ${FILE_SIZE_UNITS[unitIndex]}`;
}

/**
 * 格式化日期时间。
 * @param {string | null | undefined} dateTime 日期时间字符串。
 * @returns {string}
 */
export function formatDateTime(dateTime) {
  if (!dateTime) {
    return '--';
  }

  /** 解析后的日期对象。 */
  const parsedDate = new Date(dateTime);

  if (Number.isNaN(parsedDate.getTime())) {
    return '--';
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(parsedDate);
}
