"""接口集成测试：连接真实 MySQL，走通完整业务闭环与权限隔离。

运行前会执行 init_db --force 重建测试数据（会清空 cyf_jxrepair 库！）。
    cd backend && python -m pytest -q
"""
import io
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture(scope="module")
def client():
    subprocess.run([sys.executable, str(BACKEND / "scripts" / "init_db.py"), "--force"], check=True,
                   capture_output=True)
    from app.main import app
    with TestClient(app) as c:
        yield c


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
    r = client.post(f"/api/orders/{oid}/complete", headers=wx, json={"repair_result": "更换夹爪电磁阀并调整气压至 0.6MPa"})
    assert r.json()["data"]["status"] == "TO_ACCEPT"

    # 维修工不能验收
    assert client.post(f"/api/orders/{oid}/evaluate", headers=wx, json={"score": 5}).status_code == 403
    r = client.post(f"/api/orders/{oid}/evaluate", headers=emp, json={"score": 5, "comment": "很快"})
    detail = r.json()["data"]
    assert detail["status"] == "ARCHIVED" and detail["evaluation"]["score"] == 5
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
