"""现场照片存储：保存到 backend/uploads/yyyyMM/，数据库只存相对路径。"""
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BizError

logger = logging.getLogger("cyf.jxrepair")

# 扩展名 → 文件头魔数。只看扩展名可以被改名绕过，所以同时校验文件内容
_SIGNATURES: dict[str, tuple[str, bytes]] = {
    ".jpg": ("jpg", b"\xff\xd8\xff"),
    ".jpeg": ("jpg", b"\xff\xd8\xff"),
    ".png": ("png", b"\x89PNG\r\n\x1a\n"),
}
_URL_PREFIX = "uploads"


def _read_limited(file: UploadFile, limit: int) -> bytes:
    data = file.file.read(limit + 1)  # 多读 1 字节即可判断是否超限，不必把大文件全部读进内存
    if len(data) > limit:
        raise BizError(f"图片「{file.filename}」超过 {settings.upload_max_mb}MB")
    if not data:
        raise BizError(f"图片「{file.filename}」是空文件")
    return data


def _validate(file: UploadFile, data: bytes) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _SIGNATURES:
        raise BizError("仅支持 jpg / png 格式的图片")
    ext, magic = _SIGNATURES[suffix]
    if not data.startswith(magic):
        raise BizError(f"「{file.filename}」不是有效的 {ext} 图片")
    return ext


def save_images(files: list[UploadFile]) -> list[str]:
    """校验并保存图片，返回相对路径列表。任一张不合格则全部不保存。"""
    files = [f for f in files if f and f.filename]
    if len(files) > settings.upload_max_count:
        raise BizError(f"最多上传 {settings.upload_max_count} 张照片")

    limit = settings.upload_max_mb * 1024 * 1024
    prepared = []
    for f in files:
        data = _read_limited(f, limit)
        prepared.append((_validate(f, data), data))

    sub_dir = datetime.now().strftime("%Y%m")
    target_dir = settings.upload_dir / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for ext, data in prepared:
        name = f"{uuid.uuid4().hex}.{ext}"  # 不使用原文件名，防止路径穿越与重名覆盖
        (target_dir / name).write_bytes(data)
        saved.append(f"{_URL_PREFIX}/{sub_dir}/{name}")
    return saved


def remove_files(rel_paths: list[str] | None) -> None:
    """删除已保存的图片（用于事务回滚或替换照片时清理）。"""
    root = settings.upload_dir.resolve()
    for rel in rel_paths or []:
        path = (settings.upload_dir / rel.removeprefix(f"{_URL_PREFIX}/")).resolve()
        if path.is_relative_to(root) and path.is_file():
            try:
                path.unlink()
            except OSError:
                logger.warning("删除图片失败: %s", path)


def to_urls(rel_paths: list[str] | None) -> list[str]:
    return [f"/{p}" for p in rel_paths or []]
