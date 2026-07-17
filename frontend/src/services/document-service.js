/**
 * 功能：封装文档管理相关的接口请求，统一处理上传、列表、详情、重命名、删除和下载。
 */
import httpClient from './http';
import { buildListParams, unwrapApiResponse } from '@/utils/api';

/**
 * 获取文档分页列表。
 * @param {{ page: number, pageSize: number, knowledgeBaseId?: number | null }} filters 查询条件。
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
export async function fetchDocumentList(filters) {
  /** 列表响应对象。 */
  const response = await httpClient.get('/documents/list', {
    params: buildListParams(filters),
  });

  return unwrapApiResponse(response.data);
}

/**
 * 获取文档详情。
 * @param {number} id 文档 ID。
 * @returns {Promise<any>}
 */
export async function fetchDocumentDetail(id) {
  /** 详情响应对象。 */
  const response = await httpClient.get('/documents/detail', {
    params: { id },
  });

  return unwrapApiResponse(response.data);
}

/**
 * 上传文档。
 * @param {{ knowledgeBaseId: number, file: File }} payload 上传参数。
 * @returns {Promise<any>}
 */
export async function createDocument(payload) {
  /** 上传表单对象。 */
  const formData = new FormData();
  formData.append('knowledge_base_id', String(payload.knowledgeBaseId));
  formData.append('file', payload.file);

  /** 上传响应对象。 */
  const response = await httpClient.post('/documents/create', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return unwrapApiResponse(response.data);
}

/**
 * 重命名文档。
 * @param {{ id: number, file_name: string }} payload 更新参数。
 * @returns {Promise<any>}
 */
export async function updateDocument(payload) {
  /** 更新响应对象。 */
  const response = await httpClient.put('/documents/update', payload);

  return unwrapApiResponse(response.data);
}

/**
 * 删除文档。
 * @param {number} id 文档 ID。
 * @returns {Promise<null>}
 */
export async function deleteDocument(id) {
  /** 删除响应对象。 */
  const response = await httpClient.delete('/documents/delete', {
    params: { id },
  });

  return unwrapApiResponse(response.data);
}

/**
 * 下载文档文件。
 * @param {number} id 文档 ID。
 * @returns {Promise<Blob>}
 */
export async function downloadDocument(id) {
  /** 下载响应对象。 */
  const response = await httpClient.get('/documents/download', {
    params: { id },
    responseType: 'blob',
  });

  return response.data;
}
