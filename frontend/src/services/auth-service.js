/**
 * 功能：登录鉴权相关 API（login / register / me）。
 */
import httpClient from './http';
import { unwrapApiResponse } from '@/utils/api';

/**
 * 用户名密码登录。
 * @param {{ username: string, password: string }} payload 凭证。
 * @returns {Promise<{ access_token: string, token_type: string, user: object }>}
 */
export async function login(payload) {
  const response = await httpClient.post('/auth/login', {
    username: payload.username,
    password: payload.password,
  });
  return unwrapApiResponse(response.data);
}

/**
 * 注册新用户（成功后返回 Token，等同自动登录）。
 * @param {{ username: string, email: string, password: string }} payload 注册信息。
 * @returns {Promise<{ access_token: string, token_type: string, user: object }>}
 */
export async function register(payload) {
  const response = await httpClient.post('/auth/register', {
    username: payload.username,
    email: payload.email,
    password: payload.password,
  });
  return unwrapApiResponse(response.data);
}

/**
 * 获取当前登录用户。
 * @returns {Promise<object>}
 */
export async function fetchMe() {
  const response = await httpClient.get('/auth/me');
  return unwrapApiResponse(response.data);
}
