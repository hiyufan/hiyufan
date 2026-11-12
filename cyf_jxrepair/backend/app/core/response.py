"""统一响应格式：{code, message, data}。code=200 表示成功，其余为业务错误码。"""
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

SUCCESS_CODE = 200


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(SUCCESS_CODE, description="业务状态码，200 为成功")
    message: str = Field("操作成功", description="提示信息")
    data: T | None = Field(None, description="业务数据")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


def ok(data: T | None = None, message: str = "操作成功") -> ApiResponse[T]:
    return ApiResponse(code=SUCCESS_CODE, message=message, data=data)


def page_of(items: list[T], total: int, page: int, size: int) -> PageResult[T]:
    return PageResult(items=items, total=total, page=page, size=size)
