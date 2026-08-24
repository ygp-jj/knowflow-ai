/**
 * 功能：登录态本地存储与读写（token + user）。
 */
const TOKEN_KEY = 'knowflow_access_token';
const USER_KEY = 'knowflow_auth_user';

/**
 * 读取本地 Token。
 * @returns {string}
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

/**
 * 写入 Token。
 * @param {string} token JWT。
 * @returns {void}
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token || '');
}

/**
 * 清除 Token。
 * @returns {void}
 */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * 读取缓存的用户信息。
 * @returns {{ id: number, username: string, email?: string } | null}
 */
export function getCachedUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * 缓存用户信息。
 * @param {object | null} user 用户对象。
 * @returns {void}
 */
export function setCachedUser(user) {
  if (!user) {
    localStorage.removeItem(USER_KEY);
    return;
  }
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * 清除全部登录缓存。
 * @returns {void}
 */
export function clearAuthStorage() {
  clearToken();
  setCachedUser(null);
}
