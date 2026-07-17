/**
 * 功能：提供统一响应解包、分页参数构建和错误文案归一化等通用接口工具。
 */
/**
 * 解析前端请求使用的 API 基础地址。
 * 默认返回相对路径，便于通过同域反向代理部署到服务器。
 * @param {string | undefined | null} explicitBaseUrl 显式配置的 API 根地址。
 * @returns {string}
 */
export function resolveApiBaseUrl(explicitBaseUrl) {
  if (!explicitBaseUrl) {
    return '/api/v1';
  }

  return `${String(explicitBaseUrl).replace(/\/+$/, '')}/api/v1`;
}

/**
 * 解包统一接口响应。
 * @param {{ code: number, message: string, data: any }} payload 接口响应体。
 * @returns {any}
 */
export function unwrapApiResponse(payload) {
  if (!payload || typeof payload.code !== 'number') {
    throw new Error('接口响应格式不正确');
  }

  if (payload.code !== 0) {
    throw new Error(payload.message || '接口请求失败');
  }

  return payload.data;
}

/**
 * 构建分页列表参数。
 * @param {{ page: number, pageSize: number, ownerId?: number, knowledgeBaseId?: number | null }} filters 查询条件。
 * @returns {{ page: number, page_size: number, owner_id?: number, knowledge_base_id?: number }}
 */
export function buildListParams(filters) {
  /** 基础分页参数。 */
  const params = {
    page: filters.page,
    page_size: filters.pageSize,
  };

  if (filters.ownerId) {
    params.owner_id = filters.ownerId;
  }

  if (filters.knowledgeBaseId) {
    params.knowledge_base_id = filters.knowledgeBaseId;
  }

  return params;
}

/**
 * 归一化错误信息。
 * @param {any} error 异常对象。
 * @param {string} fallback 默认兜底文案。
 * @returns {string}
 */
export function normalizeErrorMessage(error, fallback = '请求失败，请稍后重试') {
  return error?.response?.data?.message || error?.message || fallback;
}
