/**
 * 功能：验证前端页面统一从共享配置读取默认 owner_id，避免各页面硬编码不同值。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * 读取源码文件。
 * @param {string} relativePath 源码相对路径。
 * @returns {string}
 */
function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8');
}

test('frontend pages import shared DEFAULT_OWNER_ID config', () => {
  const knowledgeBasePage = readSource('src/views/KnowledgeBasePage.vue');
  const documentPage = readSource('src/views/DocumentPage.vue');
  const adminLayout = readSource('src/layouts/AdminLayout.vue');

  assert.ok(knowledgeBasePage.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));
  assert.ok(documentPage.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));
  assert.ok(adminLayout.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));

  assert.ok(!knowledgeBasePage.includes('const DEFAULT_OWNER_ID ='));
  assert.ok(!documentPage.includes('const DEFAULT_OWNER_ID ='));
});
