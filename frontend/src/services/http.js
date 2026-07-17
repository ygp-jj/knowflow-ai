/**
 * 功能：创建统一的 Axios 请求实例，封装前端访问后端 API 的基础地址和超时配置。
 */
import axios from 'axios';
import { resolveApiBaseUrl } from '@/utils/api';

/** 接口基础地址。 */
const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

/** Axios 请求实例。 */
const httpClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export default httpClient;
