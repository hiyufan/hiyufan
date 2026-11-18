"""接口集成测试：连接真实 MySQL，走通完整业务闭环与权限隔离。

使用独立的 <DB_NAME>_test 数据库与临时上传目录，不重建业务数据库。
    cd backend && python -m pytest -q
"""
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from app.core.config import settings
    from app.core.database import get_db
    from app.services import alert_service

    # 测试专用连接与依赖覆盖，后台扫描同样不能访问业务数据库。
    test_name = settings.db_name[:59] + "_test"
    test_settings = settings.model_copy(update={"db_name": test_name})
    env = {**os.environ, "DB_NAME": test_name}
    subprocess.run([sys.executable, str(BACKEND / "scripts" / "init_db.py"), "--force"], check=True,
                   capture_output=True, env=env)
    engine = create_engine(test_settings.database_url, pool_pre_ping=True)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def test_db():
        with sessions() as db:
            yield db

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "upload_dir", tmp_path_factory.mktemp("uploads"))
        patch.setattr(alert_service, "SessionLocal", sessions)
        from app.main import app
        app.dependency_overrides[get_db] = test_db
        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.pop(get_db, None)
            engine.dispose()


def login(client, username):
    r = client.post("/api/auth/login", json={"username": username, "password": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['token']}"}


def submit(client, headers, device_id=3, desc="焊接机器人夹爪气缸动作无力，工件掉落", files=None):
    files = files if files is not None else [("photos", ("site.png", io.BytesIO(PNG), "image/png"))]
    return client.post("/api/orders", headers=headers, files=files,
                       data={"device_id": device_id, "fault_desc": desc, "urgency": "HIGH"})


def test_unified_response_and_auth(client):
    r = client.get("/api/orders")
    assert r.status_code == 401 and r.json()["code"] == 401 and r.json()["data"] is None
    r = client.post("/api/auth/login", json={"username": "emp01", "password": "wrong-pass"})
    assert r.json() == {"code": 401, "message": "账号或密码错误", "data": None}
    r = client.get("/api/not-exist")
    assert r.json()["code"] == 404


def test_full_business_loop(client):
    emp, admin, wx = login(client, "emp01"), login(client, "sbk01"), login(client, "wx03")

    r = submit(client, emp)
    assert r.json()["code"] == 200, r.text
    order = r.json()["data"]
    oid = order["id"]
    assert order["order_no"].startswith("CYF") and len(order["order_no"]) == 14
    assert order["status"] == "PENDING" and order["photo_urls"][0].startswith("/uploads/")
    assert client.get(order["photo_urls"][0]).status_code == 200

    # 越权：员工不能派单、维修工不能派单
    assert client.post(f"/api/orders/{oid}/dispatch", headers=emp, json={"repairer_id": 12}).status_code == 403
    assert client.post(f"/api/orders/{oid}/dispatch", headers=wx, json={"repairer_id": 12}).status_code == 403

    r = client.post(f"/api/orders/{oid}/dispatch", headers=admin, json={"repairer_id": 12})
    assert r.json()["data"]["status"] == "ASSIGNED"
    # 重复派单
    assert client.post(f"/api/orders/{oid}/dispatch", headers=admin, json={"repairer_id": 12}).status_code == 409

    # 其他维修工看不到也接不了
    other = login(client, "wx01")
    assert client.post(f"/api/orders/{oid}/take", headers=other).status_code == 404

    assert client.get(f"/api/orders/{oid}", headers=wx).json()["data"]["actions"] == [
        {"value": "TAKE", "label": "接单"}]
    assert client.post(f"/api/orders/{oid}/take", headers=wx).json()["data"]["status"] == "REPAIRING"
    no_category = client.post(f"/api/orders/{oid}/complete", headers=wx, json={"repair_result": "更换夹爪电磁阀"})
    assert no_category.status_code == 422  # 完工必须确认故障类别
    r = client.post(f"/api/orders/{oid}/complete", headers=wx,
                    json={"repair_result": "更换夹爪电磁阀并调整气压至 0.6MPa", "fault_category": "气动故障"})
    assert r.json()["data"]["status"] == "TO_ACCEPT"

    # 维修工不能验收
    assert client.post(f"/api/orders/{oid}/evaluate", headers=wx, json={"score": 5}).status_code == 403
    r = client.post(f"/api/orders/{oid}/evaluate", headers=emp, json={"score": 5, "comment": "很快"})
    detail = r.json()["data"]
    assert detail["status"] == "ARCHIVED" and detail["evaluation"]["score"] == 5
    assert detail["fault_category"] == "气动故障"
    assert [lg["action"] for lg in detail["logs"]] == ["SUBMIT", "DISPATCH", "TAKE", "COMPLETE", "ACCEPT", "ARCHIVE"]

    # 已归档不可再变更
    r = client.post(f"/api/orders/{oid}/accept-fail", headers=emp, json={"reason": "再改一次"})
    assert r.status_code == 409 and "已归档" in r.json()["message"]


def test_reject_and_resubmit(client):
    emp, admin = login(client, "emp02"), login(client, "sbk01")
    oid = submit(client, emp, device_id=5, desc="输送线有点问题需要看看").json()["data"]["id"]

    assert client.post(f"/api/orders/{oid}/reject", headers=admin, json={"reason": " "}).status_code == 422
    r = client.post(f"/api/orders/{oid}/reject", headers=admin, json={"reason": "请描述具体现象"})
    assert r.json()["data"]["status"] == "REJECTED"
    listed = client.get("/api/orders", headers=emp, params={"status": "REJECTED"}).json()["data"]["items"]
    assert any(o["id"] == oid and o["reject_reason"] == "请描述具体现象" for o in listed)

    r = client.post(f"/api/orders/{oid}/resubmit", headers=emp,
                    data={"device_id": 5, "fault_desc": "装配输送线皮带跑偏，物料从侧边掉落", "keep_photos": "true"})
    assert r.json()["data"]["status"] == "PENDING"
    assert r.json()["data"]["logs"][-1]["action"] == "RESUBMIT"


def test_upload_validation(client):
    emp = login(client, "emp03")
    gif = [("photos", ("a.gif", io.BytesIO(b"GIF89a"), "image/gif"))]
    assert "jpg / png" in submit(client, emp, device_id=8, files=gif).json()["message"]
    fake = [("photos", ("a.jpg", io.BytesIO(b"not an image"), "image/jpeg"))]
    assert "不是有效的" in submit(client, emp, device_id=8, files=fake).json()["message"]
    big = [("photos", ("big.jpg", io.BytesIO(JPG + b"\x00" * (5 * 1024 * 1024)), "image/jpeg"))]
    assert "5MB" in submit(client, emp, device_id=8, files=big).json()["message"]


def test_data_scope(client):
    def ids(user):
        h = login(client, user)
        return {o["reporter"]["id"] for o in client.get("/api/orders", headers=h, params={"size": 100})
                .json()["data"]["items"]}

    assert ids("emp01") == {5}
    assert ids("dept01") <= {3, 5, 6}  # 生产一部
    wx = login(client, "wx02")
    items = client.get("/api/orders", headers=wx, params={"size": 100}).json()["data"]["items"]
    assert items and all(o["repairer"]["id"] == 11 for o in items)
    assert client.get("/api/stats/summary", headers=login(client, "emp01")).status_code == 403
    assert client.get("/api/users", headers=login(client, "wx01")).status_code == 403


def test_list_filters(client):
    admin = login(client, "sbk01")
    r = client.get("/api/orders", headers=admin, params={"page": 2, "size": 5, "keyword": "注塑"}).json()["data"]
    assert r["page"] == 2 and r["size"] == 5
    assert all("注塑" in o["device"]["device_name"] or "注塑" in o["fault_desc"] for o in r["items"])
    multi = client.get("/api/orders", headers=admin, params=[("status", "PENDING"), ("status", "REJECTED")])
    assert {o["status"] for o in multi.json()["data"]["items"]} <= {"PENDING", "REJECTED"}


def test_stats_match_db(client):
    admin = login(client, "sbk01")
    summary = client.get("/api/stats/summary", headers=admin).json()["data"]
    dist = client.get("/api/stats/status", headers=admin).json()["data"]
    assert sum(i["value"] for i in dist) == summary["total"]
    for path in ("monthly", "duration", "device-ranking"):
        assert client.get(f"/api/stats/{path}", headers=admin).json()["code"] == 200


def test_ai_features(client):
    emp, admin = login(client, "emp04"), login(client, "sbk01")
    desc = "注塑机料筒温度上不去，加热圈附近有焦糊味"
    d = client.post("/api/ai/diagnose", headers=emp, json={"fault_desc": desc}).json()["data"]
    assert d["engine"] == "local-kb" and d["items"][0]["category"] == "电气故障" and d["risk_level"] == "高"
    assert all("电气故障" in r["skills"] for r in d["recommended_repairers"][:2])

    hits = client.get("/api/ai/knowledge", headers=emp, params={"q": "皮带跑偏"}).json()["data"]
    assert hits and "跑偏" in hits[0]["fault_desc"]

    cards = client.get("/api/ai/summaries", headers=admin, params={"status": "PENDING"}).json()["data"]
    assert cards and "故障类型" in cards[0]["fields"]

    client.post("/api/ai/alerts/scan", headers=admin)
    alerts = client.get("/api/ai/alerts", headers=admin).json()["data"]
    assert alerts, "测试数据中应存在超期工单"
    r = client.post(f"/api/ai/alerts/{alerts[0]['id']}/handle", headers=admin).json()
    assert r["code"] == 200, r
    assert len(client.get("/api/ai/alerts", headers=admin).json()["data"]) == len(alerts) - 1


def test_hybrid_diagnosis_uses_cases(client):
    emp = login(client, "emp04")
    # 与历史案例"冷却塔风机振动大，噪音异常"相近：规则(机械故障)与案例两路证据同时成立
    d = client.post("/api/ai/diagnose", headers=emp, json={"fault_desc": "冷却塔风机振动很大，噪音异常"}).json()["data"]
    top = d["items"][0]
    assert top["category"] == "机械故障"
    assert top["rule_confidence"] > 0 and top["case_confidence"] > 0 and top["evidence_cases"]
    # noisy-OR：合成置信度不低于任何一路证据
    assert top["confidence"] >= max(top["rule_confidence"], top["case_confidence"])


def test_recommendation_ranking(client):
    admin = login(client, "sbk01")
    ranked = client.get("/api/repairers", headers=admin, params={"category": "液压故障"}).json()["data"]
    assert [r["score"] for r in ranked] == sorted((r["score"] for r in ranked), reverse=True)
    assert ranked[0]["matched"] and "擅长液压故障" in ranked[0]["reasons"]


def test_login_lockout(client):
    for _ in range(5):
        r = client.post("/api/auth/login", json={"username": "lock_probe", "password": "wrong-pass"})
    assert r.status_code == 429
    r = client.post("/api/auth/login", json={"username": "lock_probe", "password": "wrong-pass"})
    assert r.status_code == 429 and "锁定" in r.json()["message"]


def new_device(client, admin, code):
    response = client.post("/api/devices", headers=admin, json={
        "device_code": code, "device_name": "回归测试设备", "category": "测试设备",
        "dept_id": 1, "location": "测试工位",
    })
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def test_department_alerts_follow_order_scope(client):
    admin = login(client, "sbk01")
    all_alerts = client.get("/api/ai/alerts", headers=admin).json()["data"]
    assert all_alerts
    for username in ("dept01", "dept02"):
        headers = login(client, username)
        visible = {o["id"] for o in client.get("/api/orders", headers=headers, params={"size": 100})
                   .json()["data"]["items"]}
        alerts = client.get("/api/ai/alerts", headers=headers).json()["data"]
        assert {a["order_id"] for a in alerts} == {a["order_id"] for a in all_alerts if a["order_id"] in visible}
        summary = client.get("/api/stats/summary", headers=headers).json()["data"]
        assert len(alerts) == summary["open_alerts"]
        assert any(a["order_id"] not in visible for a in all_alerts)


def test_shared_knowledge_does_not_grant_order_access(client):
    employee = login(client, "emp04")
    hits = client.get("/api/ai/knowledge", headers=employee, params={"q": "皮带跑偏"}).json()["data"]
    assert hits
    for hit in hits:
        response = client.get(f"/api/ai/knowledge/{hit['order_id']}", headers=employee)
        assert response.status_code == 200
        case = response.json()["data"]
        assert case["fault_desc"] == hit["fault_desc"] and case["repair_result"] == hit["repair_result"]
        assert set(case) == {"order_id", "order_no", "device_name", "category", "fault_desc", "repair_result", "archived_at"}
    assert client.get("/api/orders/5", headers=employee).status_code == 404
    assert client.get("/api/ai/knowledge/31", headers=employee).status_code == 404
    assert client.get("/api/ai/knowledge/999999", headers=employee).status_code == 404
    assert client.get("/api/ai/knowledge/5").status_code == 401


def test_full_length_descriptions_and_results(client):
    employee, admin, repairer = login(client, "emp01"), login(client, "sbk01"), login(client, "wx03")
    did = new_device(client, admin, "REG-LENGTH-001")
    for text in (" " * 5, "\t\n " * 5, "    异响    ", "测" * 501):
        assert submit(client, employee, device_id=did, desc=text, files=[]).status_code == 422

    description = "电机异响" + "测" * 496
    response = submit(client, employee, device_id=did, desc=description, files=[])
    assert response.status_code == 200, response.text
    order = response.json()["data"]
    oid = order["id"]
    assert order["fault_desc"] == description
    assert order["logs"][0]["content"].endswith("…")
    assert len(order["logs"][0]["content"]) == 500
    assert client.get("/api/ai/knowledge", headers=employee, params={"q": description}).status_code == 200
    assert client.post("/api/ai/diagnose", headers=employee, json={"fault_desc": description}).status_code == 200

    assert client.post(f"/api/orders/{oid}/dispatch", headers=admin, json={"repairer_id": 12}).status_code == 200
    assert client.post(f"/api/orders/{oid}/take", headers=repairer).status_code == 200
    assert client.post(f"/api/orders/{oid}/complete", headers=repairer,
                       json={"repair_result": " " * 5, "fault_category": "电气故障"}).status_code == 422
    result = "维修完成" + "测" * 496
    response = client.post(f"/api/orders/{oid}/complete", headers=repairer,
                           json={"repair_result": result, "fault_category": "电气故障"})
    assert response.status_code == 200, response.text
    order = response.json()["data"]
    assert order["repair_result"] == result
    assert len(order["logs"][-1]["content"]) == 500
    assert client.post(f"/api/orders/{oid}/evaluate", headers=employee, json={"score": 5}).status_code == 200


def test_resubmit_validates_trimmed_description(client):
    employee, admin = login(client, "emp02"), login(client, "sbk01")
    did = new_device(client, admin, "REG-RESUBMIT-001")
    order = submit(client, employee, device_id=did, desc="   电机持续异响   ", files=[]).json()["data"]
    assert order["fault_desc"] == "电机持续异响"
    oid = order["id"]
    assert client.post(f"/api/orders/{oid}/reject", headers=admin, json={"reason": "请补充故障现象"}).status_code == 200
    response = client.post(f"/api/orders/{oid}/resubmit", headers=employee,
                           data={"device_id": did, "fault_desc": " " * 10})
    assert response.status_code == 422
    description = "电机异响" + "测" * 496
    response = client.post(f"/api/orders/{oid}/resubmit", headers=employee,
                           data={"device_id": did, "fault_desc": description})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["fault_desc"] == description
    assert len(response.json()["data"]["logs"][-1]["content"]) == 500


@pytest.mark.parametrize("path,method,body", [
    ("/api/ai/knowledge", "get", {"q": " " * 10}),
    ("/api/ai/knowledge", "get", {"q": "测" * 501}),
    ("/api/ai/diagnose", "post", {"fault_desc": " " * 10}),
])
def test_ai_rejects_invalid_descriptions(client, path, method, body):
    headers = login(client, "emp04")
    if method == "get":
        response = client.get(path, headers=headers, params=body)
    else:
        response = client.post(path, headers=headers, json=body)
    assert response.status_code == 422
