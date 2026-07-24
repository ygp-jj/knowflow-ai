from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 应用配置类，自动从 .env 文件或环境变量加载配置项。
    # 字段名大小写不敏感（case_sensitive=False），习惯上用 snake_case。

    
    # ========== 应用基础配置 ==========
    app_name: str = "KnowFlow AI"          # 应用名称
    app_env: str = "development"          # 运行环境：development / production / testing
    app_debug: bool = True                # 是否开启调试模式

    # ========== 数据库与中间件 ==========
    database_url: str                     # PostgreSQL 连接串（必填，无默认值）
    redis_url: str                        # Redis 连接串
    celery_broker_url: str                # Celery 消息代理（一般也用 Redis）
    celery_result_backend: str            # Celery 结果后端

    # ========== 跨域配置 ==========
    cors_origins: str = "http://localhost:5173"  # 允许的前端域名，多个用逗号分隔

    # ========== Milvus 向量数据库 ==========
    milvus_host: str = "localhost"        # Milvus 主机地址
    milvus_port: int = 19530              # Milvus 端口
    milvus_collection: str = "document_chunks"  # 默认集合名称

    # ========== 大语言模型 (LLM) ==========
    llm_provider: str = "openai_compatible"  # 提供商类型
    llm_base_url: str                        # API 基础地址（必填）
    llm_api_key: str                         # API 密钥（必填）
    llm_model: str = "deepseek-chat"         # 模型名称

    # ========== 嵌入模型 ==========
    embedding_provider: str = "openai_compatible"
    embedding_base_url: str                   # 嵌入服务地址（必填）
    embedding_api_key: str                    # 密钥（必填）
    embedding_model: str                      # 模型名称（必填）
    embedding_dimension: int = 1024           # 向量维度

    # ========== RAG 检索参数 ==========
    rag_top_k: int = 5                        # 检索返回的文档块数量
    rag_score_threshold: float = 0.3          # 相似度阈值，低于此分数会被过滤
    rag_max_context_chars: int = 8000         # 拼接给 LLM 的最大字符数

    # ========== 文本切片参数（精准问答场景默认 256/50） ==========
    chunk_size: int = 256                     # 单块最大字符数
    chunk_overlap: int = 50                   # 相邻块重叠字符数

    # ========== MinIO 对象存储 ==========
    minio_endpoint: str = "localhost:9000"    # MinIO 服务地址
    minio_access_key: str = "minioadmin"      # MinIO 访问账号
    minio_secret_key: str = "minioadmin"      # MinIO 访问密码
    minio_bucket_name: str = "knowflow-documents"  # 文档上传桶名
    minio_secure: bool = False                # 本地开发默认使用 HTTP

    # ========== pydantic-settings 配置 ==========
    class Config:
        # 指定从当前目录的 .env 文件加载环境变量
        env_file = ".env"
        # 字段名匹配时忽略大小写（即环境变量 DATABASE_URL 对应 database_url）
        case_sensitive = False

    # ========== 计算属性 ==========
    @property
    def cors_origin_list(self) -> List[str]:
        """将 cors_origins 字符串拆分为列表，方便 FastAPI 使用。"""
        return [item.strip() for item in self.cors_origins.split(",")]


# 实例化全局配置对象，整个应用导入这个实例即可
settings = Settings()
