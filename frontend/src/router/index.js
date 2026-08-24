/**
 * 功能：定义管理台路由结构；未登录跳转 /login，已登录访问登录页则回首页。
 */
import { createRouter, createWebHistory } from 'vue-router';

import AdminLayout from '@/layouts/AdminLayout.vue';
import ChatPage from '@/views/ChatPage.vue';
import DocumentPage from '@/views/DocumentPage.vue';
import KnowledgeBasePage from '@/views/KnowledgeBasePage.vue';
import LoginPage from '@/views/LoginPage.vue';
import { getToken } from '@/stores/auth';

/** 路由配置集合。 */
const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: {
      title: '登录',
      public: true,
    },
  },
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

router.beforeEach((to) => {
  const token = getToken();
  if (to.meta?.public) {
    if (token && to.name === 'login') {
      return { path: '/knowledge-bases' };
    }
    return true;
  }
  if (!token) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    };
  }
  return true;
});

export default router;
