/**
 * 功能：验证通用 API 工具、格式化函数和文档状态映射的基础行为。
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildListParams,
  normalizeErrorMessage,
  resolveApiBaseUrl,
  unwrapApiResponse,
} from '../src/utils/api.js';
import { formatDateTime, formatFileSize } from '../src/utils/formatters.js';
import { getDocumentStatusMeta } from '../src/utils/document-status.js';

test('unwrapApiResponse returns data for successful payload', () => {
  /** @type {{ code: number, message: string, data: { id: number } }} */
  const payload = {
    code: 0,
    message: 'success',
    data: { id: 1 },
  };

  assert.deepEqual(unwrapApiResponse(payload), { id: 1 });
});

test('unwrapApiResponse throws backend message for failed payload', () => {
  /** @type {{ code: number, message: string, data: null }} */
  const payload = {
    code: 404,
    message: '知识库不存在',
    data: null,
  };

  assert.throws(() => unwrapApiResponse(payload), /知识库不存在/);
});

test('buildListParams removes empty optional filters', () => {
  /** @type {{ page: number, pageSize: number, knowledgeBaseId: number | null }} */
  const filters = {
    page: 2,
    pageSize: 20,
    knowledgeBaseId: null,
  };

  assert.deepEqual(buildListParams(filters), { page: 2, page_size: 20 });
});

test('normalizeErrorMessage prefers backend message', () => {
  /** @type {{ response: { data: { message: string } } }} */
  const error = {
    response: {
      data: {
        message: '文档删除失败',
      },
    },
  };

  assert.equal(normalizeErrorMessage(error), '文档删除失败');
});

test('resolveApiBaseUrl falls back to relative api path for server deployment', () => {
  assert.equal(resolveApiBaseUrl(''), '/api/v1');
});

test('resolveApiBaseUrl trims trailing slash from explicit base url', () => {
  assert.equal(resolveApiBaseUrl('http://10.17.223.59:8000/'), 'http://10.17.223.59:8000/api/v1');
});

test('formatFileSize renders bytes into readable units', () => {
  assert.equal(formatFileSize(512), '512 B');
  assert.equal(formatFileSize(2048), '2.0 KB');
  assert.equal(formatFileSize(1048576), '1.0 MB');
});

test('formatDateTime returns placeholder for empty values', () => {
  assert.equal(formatDateTime(''), '--');
});

/** 向量化终态 embedded 应对应 success 颜色与「已完成」文案。 */
test('getDocumentStatusMeta maps embedded state into success token', () => {
  assert.deepEqual(getDocumentStatusMeta('embedded'), {
    color: 'success',
    label: '已完成',
  });
});
