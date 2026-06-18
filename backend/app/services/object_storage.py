"""对象存储服务，封装 MinIO 上传、下载和删除。"""

from io import BytesIO

from app.core.config import settings


class ObjectStorageService:
    """MinIO 对象存储服务。"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """懒加载 MinIO 客户端，避免测试环境强依赖 SDK。"""

        if self._client is None:
            try:
                from minio import Minio
            except ImportError as exc:
                raise RuntimeError("未安装 minio 依赖，请先执行 pip install -r requirements.txt") from exc

            self._client = Minio(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            if not self._client.bucket_exists(settings.minio_bucket_name):
                self._client.make_bucket(settings.minio_bucket_name)
        return self._client

    def upload_file(self, file_bytes: bytes, object_name: str, content_type: str):
        """上传文件字节到 MinIO。"""

        client = self._get_client()
        data_stream = BytesIO(file_bytes)
        client.put_object(
            bucket_name=settings.minio_bucket_name,
            object_name=object_name,
            data=data_stream,
            length=len(file_bytes),
            content_type=content_type,
        )
        return object_name

    def download_file(self, object_name: str):
        """下载 MinIO 对象并返回字节和内容类型。"""

        client = self._get_client()
        response = client.get_object(settings.minio_bucket_name, object_name)
        try:
            return {
                "bytes": response.read(),
                "content_type": response.headers.get("Content-Type", "application/octet-stream"),
            }
        finally:
            response.close()
            response.release_conn()

    def delete_file(self, object_name: str):
        """删除 MinIO 中的对象。"""

        client = self._get_client()
        client.remove_object(settings.minio_bucket_name, object_name)


def get_object_storage():
    """提供对象存储依赖。"""

    return ObjectStorageService()
