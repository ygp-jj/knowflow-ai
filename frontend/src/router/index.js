/**
 * 功能：定义管理台路由结构，将知识库管理和文档管理页面挂载到统一后台布局。
 */
import { createRouter, createWebHistory } from 'vue-router';

import AdminLayout from '@/layouts/AdminLayout.vue';
import ChatPage from '@/views/ChatPage.vue';
import DocumentPage from '@/views/DocumentPage.vue';
import KnowledgeBasePage from '@/views/KnowledgeBasePage.vue';

/** 路由配置集合。 */
const routes = [
  {
    path: '/',
    component: AdminLayout,
    redirect: '/knowledge-bases',
    children: [
      {
        path: 'knowledge-bases',
        name: 'knowledge-bases',
        component: KnowledgeBasePage,
        meta: {
          title: '知识库管理',
        },
      },
      {
        path: 'documents',
        name: 'documents',
        component: DocumentPage,
        meta: {
          title: '文档管理',
        },
      },
      {
        path: 'chat',
        name: 'chat',
        component: ChatPage,
        meta: {
          title: '智能问答',
        },
      },
    ],
  },
];

/** 前端路由实例。 */
const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
