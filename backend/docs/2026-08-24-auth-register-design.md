# 设计：用户注册（无邮箱验证码）

> 日期：2026-08-24  
> 状态：已确认，实现中  
> 前置：JWT 登录鉴权已落地（`2026-08-24-auth-login-design.md`）

## 1. 目标

| 目标 | 不做 |
|------|------|
| `POST /api/v1/auth/register` 注册并自动签发 JWT | 邮箱验证码 / SMTP |
| 登录页同页「登录 \| 注册」切换 | 独立 `/register` 路由 |
| 演示账号仅保留 `hr_admin`，清理其余种子用户及关联数据 | 找回密码 |

## 2. 接口

- Body：`{ username, email, password }`
- 成功 data 与 login 相同：`{ access_token, token_type, user }`
- 校验：username 1–50 唯一；email 合法且唯一；password ≥ 6
- 冲突：`code=400`（用户名/邮箱已存在）

## 3. 前端

- Tab：登录 / 注册
- 登录：演示账号下拉仅 `hr_admin` + 密码
- 注册：用户名、邮箱、密码、确认密码 → 成功写 token 并进管理台

## 4. 演示数据

- 仅用户 `101 / hr_admin / demo123456`
- 删除 102/103/104 及其知识库、文档、切片、会话等关联数据
- 保留归属 `hr_admin` 的请假库、远程办公库及对应演示会话（会话 `user_id=101`）
