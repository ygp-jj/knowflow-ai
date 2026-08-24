/**
 * 功能：验证登录鉴权接入后，业务页不再依赖 DEFAULT_OWNER_ID 传参。
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

test('business pages no longer import DEFAULT_OWNER_ID', () => {
  const knowledgeBasePage = readSource('src/views/KnowledgeBasePage.vue');
  const documentPage = readSource('src/views/DocumentPage.vue');
  const chatPage = readSource('src/views/ChatPage.vue');
  const adminLayout = readSource('src/layouts/AdminLayout.vue');

  assert.ok(!knowledgeBasePage.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));
  assert.ok(!documentPage.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));
  assert.ok(!chatPage.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));
  assert.ok(!adminLayout.includes("import { DEFAULT_OWNER_ID } from '@/constants/app';"));
});

test('router guards login and http attaches bearer', () => {
  const router = readSource('src/router/index.js');
  const http = readSource('src/services/http.js');
  const loginPage = readSource('src/views/LoginPage.vue');

  assert.ok(router.includes("name: 'login'"));
  assert.ok(router.includes('beforeEach'));
  assert.ok(http.includes('Authorization'));
  assert.ok(http.includes('401'));
  assert.ok(loginPage.includes("'/auth/login'") || loginPage.includes('login('));
});
