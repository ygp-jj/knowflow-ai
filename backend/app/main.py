from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.user import User as _User  # Register the users table for ORM foreign keys.
from app.models.chat import (  # noqa: F401 — 注册 chat_* 表，供 FK / create_all 使用
    ChatMessage as _ChatMessage,
    ChatReference as _ChatReference,
    ChatSession as _ChatSession,
)
# 导入各个业务模块的路由
from app.api.v1 import documents, chat, knowledge_bases, prompts, models, evaluations





# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,     # 显示在 Swagger 文档顶部的应用名
    debug=settings.app_debug,    # 调试模式，开发时开启，生产关闭
)

# 配置跨域资源共享（CORS），允许前端跨域访问后端接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # 允许的前端地址列表
    allow_credentials=True,                  # 允许携带身份凭证（如 Cookie）
    allow_methods=["*"],                     # 允许所有 HTTP 方法
    allow_headers=["*"],                     # 允许所有请求头
)

# ---------- 注册 v1 版本的路由 ----------
# 知识库管理
app.include_router(
    knowledge_bases.router,
    prefix="/api/v1/knowledge-bases",
    tags=["Knowledge Bases"]   # Swagger 文档中的分组标签
)
# 文档管理
app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["Documents"]
)
# 对话接口
app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["Chat"]
)
# 提示词管理
app.include_router(
    prompts.router,
    prefix="/api/v1/prompts",
    tags=["Prompts"]
)
# 模型管理
app.include_router(
    models.router,
    prefix="/api/v1/models",
    tags=["Models"]
)
# 评测接口
app.include_router(
    evaluations.router,
    prefix="/api/v1/evaluations",
    tags=["Evaluations"]
)

# 健康检查端点，用于监控服务是否存活
@app.get("/health")
def health_check():
    """
    返回应用状态和名称。
    示例：{"status": "ok", "app": "KnowFlow AI"}
    """
    return {"status": "ok", "app": settings.app_name}
