/**
 * 功能：提供文件大小和日期时间等管理台展示格式化工具。
 */
/** 文件大小单位列表。 */
const FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB'];

/** 常见 MIME 到短扩展名的映射，兼容历史脏数据。 */
const MIME_TO_EXTENSION = {
  'application/pdf': 'pdf',
  'application/msword': 'doc',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'application/vnd.ms-excel': 'xls',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
  'application/vnd.ms-powerpoint': 'ppt',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
  'text/plain': 'txt',
  'text/markdown': 'md',
  'application/json': 'json',
  'text/csv': 'csv',
};

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
 * 格式化文件类型为短扩展名展示。
 * @param {string | null | undefined} fileType 后端返回的 file_type。
 * @param {string | null | undefined} fileName 可选文件名，用于兜底解析扩展名。
 * @returns {string}
 */
export function formatFileType(fileType, fileName) {
  /** 规范化后的类型字符串。 */
  const normalizedType = typeof fileType === 'string' ? fileType.trim().toLowerCase() : '';

  if (normalizedType) {
    if (!normalizedType.includes('/')) {
      return normalizedType.replace(/^\./, '');
    }

    /** MIME 映射命中的短扩展名。 */
    const mappedExtension = MIME_TO_EXTENSION[normalizedType];
    if (mappedExtension) {
      return mappedExtension;
    }
  }

  if (typeof fileName === 'string' && fileName.includes('.')) {
    /** 从文件名截取的扩展名。 */
    const extension = fileName.split('.').pop()?.trim().toLowerCase();
    if (extension) {
      return extension;
    }
  }

  return normalizedType || '--';
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
