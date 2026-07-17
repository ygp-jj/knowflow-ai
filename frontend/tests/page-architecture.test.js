/**
 * 功能：验证页面直接调用 service，请求状态保留在页面内部，而不是依赖 Pinia store。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/** 读取源码文件。 */
function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8');
}

test('main entry no longer installs pinia', () => {
  const source = readSource('src/main.js');

  assert.ok(!source.includes('createPinia'));
  assert.ok(!source.includes('app.use(createPinia())'));
});

test('knowledge base page requests data directly without store import', () => {
  const source = readSource('src/views/KnowledgeBasePage.vue');

  assert.ok(!source.includes('@/stores/knowledge-base'));
});

test('document page requests data directly without store import', () => {
  const source = readSource('src/views/DocumentPage.vue');

  assert.ok(!source.includes('@/stores/document'));
  assert.ok(!source.includes('@/stores/knowledge-base'));
});
