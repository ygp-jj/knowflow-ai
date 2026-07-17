/**
 * 功能：集中维护前端应用级默认配置，便于本地联调和后续接入登录态替换。
 */

/**
 * 前端默认使用的 owner_id。
 */
export const DEFAULT_OWNER_ID = Number.parseInt(import.meta.env.VITE_DEFAULT_OWNER_ID || '101', 10);
