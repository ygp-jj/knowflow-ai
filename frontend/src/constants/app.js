/**
 * 功能：集中维护前端应用级默认配置。
 *
 * 说明：登录鉴权上线后，业务身份以 JWT 为准；本文件仅保留历史联调常量供迁移参考。
 */

/**
 * @deprecated 已由 JWT 登录态替代，业务请求勿再传 owner_id / user_id。
 */
export const DEFAULT_OWNER_ID = Number.parseInt(import.meta.env.VITE_DEFAULT_OWNER_ID || '101', 10);
