"""应用入口：python -m uvicorn app.main:app --reload（在 backend 目录下执行）

一个进程同时提供：
    /api/*      REST 接口
    /docs       FastAPI 自动生成的接口文档（Swagger UI）
    /uploads/*  现场照片
    /           前端页面（frontend 目录）
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import PROJECT_DIR, settings
from app.core.exceptions import register_exception_handlers
from app.routers import ai, auth, devices, meta, orders, stats, users
from app.services.alert_service import run_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

FRONTEND_DIR = PROJECT_DIR / "frontend"
SWAGGER_DIR = Path(__file__).resolve().parent / "static" / "swagger"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stop = asyncio.Event()
    task = asyncio.create_task(run_scheduler(stop))  # 超期预警定时任务
    yield
    stop.set()
    await task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="设备报修与维修工单管理系统 REST 接口。先调用 **/api/auth/login** 获取 token，"
                "再点击右上角 **Authorize** 填入 token 即可调试需要登录的接口。",
    lifespan=lifespan,
    docs_url=None,   # 默认 /docs 从外网 CDN 加载 Swagger UI，考场断网会白屏，改为下面的本地版本
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,  # 通配源不能与携带凭证同时开启（浏览器规范）
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

for module in (auth, users, devices, orders, stats, ai, meta):
    app.include_router(module.router)


@app.get("/api/health", tags=["基础数据"], summary="健康检查")
def health():
    return {"code": 200, "message": "ok", "data": {"app": settings.app_name}}


@app.get("/docs", include_in_schema=False)
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.app_name} - 接口文档",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/swagger/favicon-32x32.png",
        swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none", "defaultModelsExpandDepth": -1},
    )


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/login.html")


app.mount("/static/swagger", StaticFiles(directory=SWAGGER_DIR), name="swagger")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir, check_dir=False), name="uploads")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
