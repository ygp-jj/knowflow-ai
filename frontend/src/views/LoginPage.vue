<template>
  <div class="login-page">
    <div class="login-page__panel">
      <div class="login-page__brand">
        <div class="login-page__mark">KF</div>
        <div>
          <h1>KnowFlow AI</h1>
          <p>登录后管理知识库与智能问答</p>
        </div>
      </div>

      <ATabs v-model:activeKey="activeTab" class="login-page__tabs">
        <ATabPane key="login" tab="登录">
          <AForm layout="vertical" :model="loginForm" @finish="handleLogin">
            <AFormItem
              label="用户名"
              name="username"
              :rules="[{ required: true, message: '请输入用户名' }]"
            >
              <AInput
                v-model:value="loginForm.username"
                size="large"
                placeholder="用户名（演示可用 hr_admin）"
                autocomplete="username"
                allow-clear
              />
            </AFormItem>
            <AFormItem
              label="密码"
              name="password"
              :rules="[{ required: true, message: '请输入密码' }]"
            >
              <AInputPassword
                v-model:value="loginForm.password"
                size="large"
                placeholder="演示密码 demo123456"
                autocomplete="current-password"
              />
            </AFormItem>
            <AButton type="primary" html-type="submit" size="large" block :loading="submitting">
              登录
            </AButton>
          </AForm>
        </ATabPane>

        <ATabPane key="register" tab="注册">
          <AForm layout="vertical" :model="registerForm" @finish="handleRegister">
            <AFormItem
              label="用户名"
              name="username"
              :rules="[{ required: true, message: '请输入用户名' }]"
            >
              <AInput
                v-model:value="registerForm.username"
                size="large"
                placeholder="设置用户名"
                autocomplete="username"
              />
            </AFormItem>
            <AFormItem
              label="邮箱"
              name="email"
              :rules="[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '邮箱格式不正确' },
              ]"
            >
              <AInput
                v-model:value="registerForm.email"
                size="large"
                placeholder="name@example.com"
                autocomplete="email"
              />
            </AFormItem>
            <AFormItem
              label="密码"
              name="password"
              :rules="[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少 6 位' },
              ]"
            >
              <AInputPassword
                v-model:value="registerForm.password"
                size="large"
                placeholder="至少 6 位"
                autocomplete="new-password"
              />
            </AFormItem>
            <AFormItem
              label="确认密码"
              name="confirmPassword"
              :rules="[
                { required: true, message: '请再次输入密码' },
                { validator: validateConfirmPassword },
              ]"
            >
              <AInputPassword
                v-model:value="registerForm.confirmPassword"
                size="large"
                placeholder="再次输入密码"
                autocomplete="new-password"
              />
            </AFormItem>
            <AButton type="primary" html-type="submit" size="large" block :loading="submitting">
              注册并登录
            </AButton>
          </AForm>
        </ATabPane>
      </ATabs>
    </div>
  </div>
</template>

<script setup>
/**
 * 功能：登录 / 注册同页；注册成功后自动写入 token 并进入管理台。
 */
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { message } from 'ant-design-vue';

import { login, register } from '@/services/auth-service';
import { setCachedUser, setToken } from '@/stores/auth';
import { normalizeErrorMessage } from '@/utils/api';

const router = useRouter();
const route = useRoute();

/** 当前 Tab：login | register。 */
const activeTab = ref('login');
const submitting = ref(false);

const loginForm = reactive({
  username: '',
  password: '',
});

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
});

/**
 * 校验确认密码。
 * @param {*} _rule 规则。
 * @param {string} value 确认密码。
 * @returns {Promise<void>}
 */
async function validateConfirmPassword(_rule, value) {
  if (value !== registerForm.password) {
    return Promise.reject(new Error('两次输入的密码不一致'));
  }
  return Promise.resolve();
}

/**
 * 登录或注册成功后写入本地态并跳转。
 * @param {{ access_token: string, user: object }} data 鉴权响应。
 * @param {string} welcomePrefix 欢迎前缀。
 * @returns {Promise<void>}
 */
async function finishAuth(data, welcomePrefix) {
  setToken(data.access_token);
  setCachedUser(data.user);
  message.success(`${welcomePrefix}，${data.user.username}`);
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/knowledge-bases';
  await router.replace(redirect || '/knowledge-bases');
}

/**
 * 提交登录。
 * @returns {Promise<void>}
 */
async function handleLogin() {
  submitting.value = true;
  try {
    const data = await login({
      username: loginForm.username.trim(),
      password: loginForm.password,
    });
    await finishAuth(data, '欢迎');
  } catch (error) {
    message.error(normalizeErrorMessage(error, '登录失败'));
  } finally {
    submitting.value = false;
  }
}

/**
 * 提交注册（成功即自动登录）。
 * @returns {Promise<void>}
 */
async function handleRegister() {
  submitting.value = true;
  try {
    const data = await register({
      username: registerForm.username.trim(),
      email: registerForm.email.trim(),
      password: registerForm.password,
    });
    await finishAuth(data, '注册成功');
  } catch (error) {
    message.error(normalizeErrorMessage(error, '注册失败'));
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.login-page {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.18), transparent 40%),
    linear-gradient(160deg, #0d2238 0%, #1a3a5c 45%, #f1f5f9 45%);
}

.login-page__panel {
  width: min(420px, 100%);
  padding: 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
}

.login-page__brand {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
}

.login-page__mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #fff;
  font-weight: 800;
}

.login-page__brand h1 {
  margin: 0;
  font-size: 24px;
  color: #122033;
}

.login-page__brand p {
  margin: 4px 0 0;
  color: #5a6b81;
  font-size: 13px;
}

.login-page__tabs :deep(.ant-tabs-nav) {
  margin-bottom: 20px;
}
</style>
