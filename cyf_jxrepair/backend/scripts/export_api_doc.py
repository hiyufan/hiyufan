"""从 FastAPI 的 OpenAPI 定义自动生成 docs/接口清单.md，保证文档与代码完全一致。

用法（在 backend 目录下）：python scripts/export_api_doc.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import PROJECT_DIR  # noqa: E402
from app.main import app  # noqa: E402

OUTPUT = PROJECT_DIR / "docs" / "接口清单.md"

# 典型返回示例（其余接口返回结构见"返回 data"列）
EXAMPLES = {
    ("post", "/api/auth/login"): {
        "code": 200, "message": "登录成功",
        "data": {"token": "eyJhbGciOiJIUzI1NiIs...", "expires_in": 28800,
                 "user": {"id": 5, "username": "emp01", "real_name": "林志强", "role": "EMPLOYEE",
                          "role_label": "普通员工", "dept_name": "生产一部", "factory_area": "A厂区"}},
    },
    ("get", "/api/orders"): {
        "code": 200, "message": "操作成功",
        "data": {"items": [{"id": 38, "order_no": "CYF20261112001", "status": "PENDING", "status_label": "待派单",
                            "device": {"device_name": "数控车床", "device_code": "CNC-A-001"},
                            "reporter": {"real_name": "陈立华"}, "repairer": None, "is_overdue": False}],
                 "total": 38, "page": 1, "size": 10},
    },
    ("post", "/api/orders/{order_id}/dispatch"): {
        "code": 200, "message": "派单成功",
        "data": {"id": 38, "status": "ASSIGNED", "status_label": "待接单",
                 "actions": [], "logs": [{"action": "DISPATCH", "content": "派单给维修工 杨帆"}]},
    },
    ("post", "/api/orders/{order_id}/evaluate"): {
        "code": 403, "message": "维修工无权执行「验收通过」", "data": None,
    },
    ("post", "/api/ai/diagnose"): {
        "code": 200, "message": "操作成功",
        "data": {"engine": "local-kb", "risk_level": "高",
                 "items": [{"category": "电气故障", "cause": "加热圈烧断、热电偶损坏或温控器故障",
                            "confidence": 0.75, "matched_keywords": ["加热圈", "温度上不去"]}],
                 "recommended_repairers": [{"real_name": "何振宇", "active_orders": 1, "matched": True}]},
    },
}


def _ref_name(schema: dict) -> str:
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if schema.get("type") == "array":
        return f"{_ref_name(schema.get('items', {}))}[]"
    if "anyOf" in schema:
        return " | ".join(_ref_name(s) for s in schema["anyOf"] if s.get("type") != "null")
    return schema.get("type", "object")


def _params(op: dict, spec: dict) -> str:
    parts = []
    for p in op.get("parameters", []):
        req = "*" if p.get("required") else ""
        parts.append(f"`{p['name']}`{req}（{p['in']}）")
    body = op.get("requestBody", {}).get("content", {})
    for ctype, content in body.items():
        schema = content["schema"]
        name = _ref_name(schema)
        fields = spec["components"]["schemas"].get(name, {})
        required = set(fields.get("required", []))
        names = [f"`{k}`{'*' if k in required else ''}" for k in fields.get("properties", {})]
        kind = "form" if "multipart" in ctype else "json"
        parts.append(f"{kind}：{'、'.join(names)}")
    return "<br>".join(parts) or "—"


def _data_type(op: dict) -> str:
    schema = op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
    raw = _ref_name(schema).removeprefix("ApiResponse_").rstrip("_")
    if raw.startswith("PageResult_"):
        return f"分页 {raw.removeprefix('PageResult_').rstrip('_')}"
    if raw.startswith("list_"):
        return f"{raw.removeprefix('list_').rstrip('_')}[]"
    if raw.startswith("dict_"):
        return "{状态: 数量}"
    return {"NoneType": "null", "dict": "object"}.get(raw, raw) or "—"


def main() -> None:
    spec = app.openapi()
    rows, n = [], 0
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            n += 1
            tag = (op.get("tags") or ["—"])[0]
            cells = [str(n), tag, f"`{method.upper()}`", f"`{path}`", op.get("summary", ""), _params(op, spec), _data_type(op)]
            rows.append(f"| {' | '.join(cells)} |")

    examples = "\n\n".join(
        f"**{m.upper()} {p}**\n\n```json\n{json.dumps(body, ensure_ascii=False, indent=2)}\n```"
        for (m, p), body in EXAMPLES.items()
    )
    OUTPUT.write_text(f"""# 接口清单

> 本文件由 `backend/scripts/export_api_doc.py` 根据 FastAPI 的 OpenAPI 定义自动生成，与代码保持一致。
> 在线调试：启动后访问 <http://127.0.0.1:8000/docs>，先调用登录接口拿到 token，再点右上角 **Authorize** 填入。

## 通用约定

- 所有接口返回统一结构：`{{"code": 200, "message": "提示信息", "data": 业务数据}}`；`code` 非 200 表示失败。
- 错误码：`401` 未登录/登录失效，`403` 无权限，`404` 不存在或无权查看，
  `409` 状态冲突（如重复派单、已归档），`422` 参数校验失败，`500` 服务器异常。
- 除登录、部门列表、枚举选项、健康检查外，其余接口需在请求头携带
  `Authorization: Bearer <token>`。
- 参数后带 `*` 为必填；`query` 为地址栏参数，`path` 为路径参数，`json` 为 JSON 请求体，`form` 为 multipart 表单。

## 接口总表（共 {n} 个）

| # | 模块 | 方法 | 地址 | 说明 | 请求参数 | 返回 data |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## 返回示例

{examples}
""", encoding="utf-8")
    print(f"已生成 {OUTPUT}（{n} 个接口）")


if __name__ == "__main__":
    main()
