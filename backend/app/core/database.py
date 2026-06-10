from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# 创建数据库引擎，用于管理连接池
engine = create_engine(
    settings.database_url,    # 数据库连接 URL，如 PostgreSQL
    pool_pre_ping=True,       # 每次从连接池取出连接时先测试连通性
    pool_size=10,             # 连接池常驻连接数
    max_overflow=20,          # 连接池满后额外可创建的最大连接数
)

# 会话工厂，用于创建数据库会话实例
SessionLocal = sessionmaker(
    autocommit=False,         # 禁用自动提交，需手动 commit
    autoflush=False,          # 禁用自动 flush，避免意外触发数据库同步
    bind=engine,              # 绑定到上面创建的引擎
)

# 声明式基类，所有 ORM 模型都将继承此类
class Base(DeclarativeBase):
    """SQLAlchemy 声明式模型基类。"""
    pass

# FastAPI 依赖注入函数，为每个请求提供独立的数据库会话
def get_db():
    """
    生成器函数，创建数据库会话并在请求结束后关闭。
    用法：在 FastAPI 路由中通过 Depends(get_db) 注入。
    """
    db = SessionLocal()       # 创建一个新会话
    try:
        yield db              # 将会话提供给路由函数
    finally:
        db.close()            # 请求结束时关闭会话，归还连接到池中