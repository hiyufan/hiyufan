"""业务异常与全局异常处理：所有错误都转换成统一的 {code, message, data} 结构返回。"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("cyf.jxrepair")


class BizError(Exception):
    """业务异常。code 同时作为 HTTP 状态码，前端只需判断 body.code。"""

    def __init__(self, message: str, code: int = 400, data: object | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data


class Unauthorized(BizError):
    def __init__(self, message: str = "登录已失效，请重新登录"):
        super().__init__(message, 401)


class Forbidden(BizError):
    def __init__(self, message: str = "无权执行该操作"):
        super().__init__(message, 403)


class NotFound(BizError):
    def __init__(self, message: str = "数据不存在"):
        super().__init__(message, 404)


class Conflict(BizError):
    def __init__(self, message: str):
        super().__init__(message, 409)


def _body(code: int, message: str, data: object | None = None) -> dict:
    return {"code": code, "message": message, "data": data}


# 校验错误中常见字段的中文名，让提示更友好
_FIELD_LABELS = {
    "username": "账号", "password": "密码", "real_name": "姓名", "device_id": "报修设备",
    "fault_desc": "故障描述", "repairer_id": "维修工", "reason": "原因", "score": "评分",
    "repair_result": "处理结果", "device_code": "设备编号", "device_name": "设备名称",
    "photos": "现场照片", "page": "页码", "size": "每页条数",
}


def _validation_message(exc: RequestValidationError) -> str:
    first = exc.errors()[0]
    field = next((str(p) for p in reversed(first.get("loc", ())) if isinstance(p, str)), "")
    label = _FIELD_LABELS.get(field, field)
    msg = first.get("msg", "参数错误").removeprefix("Value error, ")
    return f"{label}：{msg}" if label else msg


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def biz_error_handler(_: Request, exc: BizError):
        return JSONResponse(status_code=exc.code, content=_body(exc.code, exc.message, exc.data))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=_body(422, _validation_message(exc)))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        message = {404: "接口或资源不存在", 405: "请求方式不被允许"}.get(exc.status_code, str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=_body(exc.status_code, message))

    @app.exception_handler(IntegrityError)
    async def integrity_handler(_: Request, exc: IntegrityError):
        logger.warning("数据约束冲突: %s", exc.orig)
        return JSONResponse(status_code=409, content=_body(409, "数据已存在或仍被引用，操作失败"))

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception):
        # 不把 str(exc) 返回前端，避免泄露 SQL 与表结构
        logger.exception("未处理异常: %s", exc)
        return JSONResponse(status_code=500, content=_body(500, "服务器开小差了，请稍后重试"))
