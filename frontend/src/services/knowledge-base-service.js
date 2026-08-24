/**
 * 功能：封装知识库管理相关的接口请求，统一对接 CRUD 和详情查询能力。
 * 身份由 JWT Bearer 决定，前端不再传 owner_id。
 */
import httpClient from './http';
import { buildListParams, unwrapApiResponse } from '@/utils/api';

/**
 * 获取知识库分页列表。
 * @param {{ page: number, pageSize: number }} filters 分页条件。
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
export async function fetchKnowledgeBaseList(filters) {
  /** 列表响应对象。 */
  const response = await httpClient.get('/knowledge-bases/list', {
    params: buildListParams(filters),
  });

  return unwrapApiResponse(response.data);
}

/**
 * 获取知识库详情。
 * @param {number} id 知识库 ID。
 * @returns {Promise<any>}
 */
export async function fetchKnowledgeBaseDetail(id) {
  /** 详情响应对象。 */
  const response = await httpClient.get('/knowledge-bases/detail', {
    params: { id },
  });

  return unwrapApiResponse(response.data);
}

/**
 * 创建知识库。
 * @param {{ name: string, description: string }} payload 创建参数。
 * @returns {Promise<any>}
 */
export async function createKnowledgeBase(payload) {
  /** 创建响应对象。 */
  const response = await httpClient.post('/knowledge-bases/create', {
    name: payload.name,
    description: payload.description,
  });

  return unwrapApiResponse(response.data);
}

/**
 * 更新知识库。
 * @param {{ id: number, name: string, description: string }} payload 更新参数。
 * @returns {Promise<any>}
 */
export async function updateKnowledgeBase(payload) {
  /** 更新响应对象。 */
  const response = await httpClient.put('/knowledge-bases/update', {
    id: payload.id,
    name: payload.name,
    description: payload.description,
  });

  return unwrapApiResponse(response.data);
}

/**
 * 删除知识库。
 * @param {number} id 知识库 ID。
 * @returns {Promise<null>}
 */
export async function deleteKnowledgeBase(id) {
  /** 删除响应对象。 */
  const response = await httpClient.delete('/knowledge-bases/delete', {
    params: { id },
  });

  return unwrapApiResponse(response.data);
}
