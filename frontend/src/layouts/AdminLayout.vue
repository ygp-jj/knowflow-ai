<template>
  <ALayout class="admin-layout">
    <ALayoutSider
      :collapsed="collapsed"
      :trigger="null"
      breakpoint="lg"
      collapsible
      class="admin-layout__sider"
      @breakpoint="handleBreakpoint"
    >
      <div class="admin-layout__brand">
        <div class="admin-layout__brand-mark">KF</div>
        <div v-if="!collapsed" class="admin-layout__brand-copy">
          <strong>KnowFlow AI</strong>
          <span>RAG 管理后台</span>
        </div>
      </div>

      <AMenu
        :selected-keys="[String(route.name || '')]"
        theme="dark"
        mode="inline"
        class="admin-layout__menu"
      >
        <AMenuItem key="knowledge-bases" @click="navigateTo('knowledge-bases')">
          <template #icon>
            <DatabaseOutlined />
          </template>
          <span>知识库管理</span>
        </AMenuItem>
        <AMenuItem key="documents" @click="navigateTo('documents')">
          <template #icon>
            <FileTextOutlined />
          </template>
          <span>文档管理</span>
        </AMenuItem>
        <AMenuItem key="chat" @click="navigateTo('chat')">
          <template #icon>
            <MessageOutlined />
          </template>
          <span>智能问答</span>
        </AMenuItem>
      </AMenu>
    </ALayoutSider>

    <ALayout>
      <ALayoutHeader class="admin-layout__header">
        <div>
          <div class="admin-layout__eyebrow">KnowFlow AI Console</div>
          <h1 class="admin-layout__title">{{ currentTitle }}</h1>
        </div>
        <div class="admin-layout__header-actions">
          <div class="admin-layout__user" :title="userEmail || undefined">
            <span class="admin-layout__user-label">用户名</span>
            <strong class="admin-layout__user-name">{{ displayName }}</strong>
            <span v-if="userEmail && userEmail !== displayName" class="admin-layout__user-email">
              {{ userEmail }}
            </span>
          </div>
          <AButton type="default" @click="handleLogout">退出登录</AButton>
          <AButton type="text" class="admin-layout__toggle" @click="toggleCollapsed">
            <MenuFoldOutlined v-if="!collapsed" />
            <MenuUnfoldOutlined v-else />
          </AButton>
        </div>
      </ALayoutHeader>

      <ALayoutContent class="admin-layout__content">
        <RouterView />
      </ALayoutContent>
    </ALayout>
  </ALayout>
</template>

<script setup>
/** 功能：提供后台通用布局、左侧导航和顶部标题区域。 */
import { computed, onMounted, ref } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';
import {
  DatabaseOutlined,
  FileTextOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MessageOutlined,
} from '@ant-design/icons-vue';
import { fetchMe } from '@/services/auth-service';
import { clearAuthStorage, getCachedUser, setCachedUser } from '@/stores/auth';

/** 是否折叠侧边栏。 */
const collapsed = ref(false);
/** 当前登录用户（顶栏展示用）。 */
const currentUser = ref(getCachedUser());
/** 当前路由对象。 */
const route = useRoute();
/** 路由实例。 */
const router = useRouter();

/** 当前页面标题。 */
const currentTitle = computed(() => route.meta?.title || '管理台');

/** 顶栏展示的用户名。 */
const displayName = computed(() => currentUser.value?.username || '已登录');

/** 顶栏展示的邮箱（与用户名不同时才显示）。 */
const userEmail = computed(() => currentUser.value?.email || '');

onMounted(async () => {
  try {
    /** 从服务端拉取最新用户信息，避免本地缓存缺字段。 */
    const me = await fetchMe();
    currentUser.value = me;
    setCachedUser(me);
  } catch {
    currentUser.value = getCachedUser();
  }
});

/**
 * 切换侧边栏折叠状态。
 * @returns {void}
 */
function toggleCollapsed() {
  collapsed.value = !collapsed.value;
}

/**
 * 根据断点更新折叠状态。
 * @param {boolean} broken 是否进入断点模式。
 * @returns {void}
 */
function handleBreakpoint(broken) {
  collapsed.value = broken;
}

/**
 * 导航到指定路由。
 * @param {string} name 路由名称。
 * @returns {void}
 */
function navigateTo(name) {
  router.push({ name });
}

/**
 * 退出登录：清 token 并跳转登录页。
 * @returns {void}
 */
function handleLogout() {
  clearAuthStorage();
  router.push({ name: 'login' });
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
  background: transparent;
}

.admin-layout__sider {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(180deg, #0d2238 0%, #13385b 100%) !important;
  box-shadow: 12px 0 40px rgba(15, 23, 42, 0.16);
}

.admin-layout__brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 26px 18px 18px;
}

.admin-layout__brand-mark {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #fff;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.admin-layout__brand-copy {
  display: flex;
  flex-direction: column;
  color: #f8fafc;
}

.admin-layout__brand-copy span {
  color: rgba(248, 250, 252, 0.72);
  font-size: 12px;
}

.admin-layout__menu {
  background: transparent !important;
  border-inline-end: none;
}

.admin-layout__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: auto;
  margin: 20px 20px 0;
  padding: 18px 24px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  line-height: 1.2;
  backdrop-filter: blur(18px);
}

.admin-layout__eyebrow {
  margin-bottom: 8px;
  color: #5a6b81;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.admin-layout__title {
  margin: 0;
  color: #122033;
  font-size: 28px;
}

.admin-layout__header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.admin-layout__user {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  max-width: 240px;
  padding: 8px 12px;
  border: 1px solid rgba(37, 99, 235, 0.25);
  border-radius: 12px;
  background: rgba(239, 246, 255, 0.9);
  line-height: 1.2;
}

.admin-layout__user-label {
  color: #64748b;
  font-size: 11px;
}

.admin-layout__user-name {
  overflow: hidden;
  color: #1d4ed8;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-layout__user-email {
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-layout__toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(241, 245, 249, 0.9);
}

.admin-layout__content {
  padding: 20px;
}

@media (max-width: 960px) {
  .admin-layout__header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
