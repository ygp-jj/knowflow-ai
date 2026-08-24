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

      <AForm layout="vertical" :model="form" @finish="handleSubmit">
        <AFormItem
          label="用户名"
          name="username"
          :rules="[{ required: true, message: '请选择用户名' }]"
        >
          <ASelect
            v-model:value="form.username"
            size="large"
            placeholder="请选择演示账号"
            :options="demoUserOptions"
          />
        </AFormItem>
        <AFormItem
          label="密码"
          name="password"
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <AInputPassword
            v-model:value="form.password"
            size="large"
            placeholder="演示密码 demo123456"
            autocomplete="current-password"
          />
        </AFormItem>
        <AButton type="primary" html-type="submit" size="large" block :loading="submitting">
          登录
        </AButton>
      </AForm>
    </div>
  </div>
</template>

<script setup>
/**
 * 功能：登录页；成功后写入 token 并跳转业务首页。
 */
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { message } from 'ant-design-vue';

import { login } from '@/services/auth-service';
import { setCachedUser, setToken } from '@/stores/auth';
import { normalizeErrorMessage } from '@/utils/api';

const router = useRouter();
const route = useRoute();

/** 演示账号下拉（与 Neon seed 用户一致，密码均为 demo123456）。 */
const demoUserOptions = [
  { value: 'hr_admin', label: 'hr_admin（人事管理员）' },
  { value: 'finance_admin', label: 'finance_admin（财务管理员）' },
  { value: 'ops_admin', label: 'ops_admin（运营管理员）' },
  { value: 'employee_demo', label: 'employee_demo（员工演示）' },
];

const form = reactive({
  username: 'hr_admin',
  password: '',
});
const submitting = ref(false);

/**
 * 提交登录。
 * @returns {Promise<void>}
 */
async function handleSubmit() {
  submitting.value = true;
  try {
    const data = await login({
      username: form.username.trim(),
      password: form.password,
    });
    setToken(data.access_token);
    setCachedUser(data.user);
    message.success(`欢迎，${data.user.username}`);
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/knowledge-bases';
    await router.replace(redirect || '/knowledge-bases');
  } catch (error) {
    message.error(normalizeErrorMessage(error, '登录失败'));
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
  margin-bottom: 28px;
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
</style>
