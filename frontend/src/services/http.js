/**
 * 功能：创建统一的 Axios 请求实例；自动附加 Bearer，401 时清登录态并跳转登录页。
 */
import axios from 'axios';
import { resolveApiBaseUrl } from '@/utils/api';
import { clearAuthStorage, getToken } from '@/stores/auth';

/** 接口基础地址。 */
const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

/** Axios 请求实例。 */
const httpClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

httpClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      clearAuthStorage();
      const path = window.location?.pathname || '';
      if (path !== '/login') {
        window.location.assign(`/login?redirect=${encodeURIComponent(path)}`);
      }
    }
    return Promise.reject(error);
  },
);

export default httpClient;
