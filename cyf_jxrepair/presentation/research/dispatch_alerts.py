"""Reproduce slides 8/10 using a NEW seeded, isolated database, never production.

Use DB_NAME=cyf_jxrepair_bench_<unique>, initialize with scripts/init_db.py,
then run this file using backend dependencies. Creates no schema; mutates fixtures.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import AlertType, OrderAction, UserRole
from app.models import OrderAlert, OrderLog, RepairOrder, User
from app.services import alert_service, user_service
from sqlalchemy import func, select


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 18, 12, 0, 0)


if not settings.db_name.startswith("cyf_jxrepair_bench_"):
    raise SystemExit("Requires a new cyf_jxrepair_bench_ database; production forbidden")

result = {
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
    "scope": "38 seeded orders, fixed application clock 2026-11-18 12:00, isolated MariaDB; sequential scans",
    "source_sha256": {name: hashlib.sha256((ROOT / "backend/app/services" / name).read_bytes()).hexdigest()
                      for name in ("user_service.py", "alert_service.py")},
    "weights": user_service.RECOMMEND_WEIGHTS,
    "ranking": {},
}
with SessionLocal() as db, patch.object(alert_service, "datetime", Clock), patch.object(alert_service.order_service, "datetime", Clock):
    assert db.scalar(select(func.count()).select_from(RepairOrder)) == 38, "Requires untouched seed"
    assert db.scalar(select(func.count()).select_from(OrderAlert)) == 0, "Requires no prior alerts"
    for category in ("气动故障", "电气故障"):
        rows = []
        for candidate in user_service.recommend_repairers(db, category):
            row = candidate.model_dump()
            row["contributions"] = [
                .4 * candidate.matched,
                .3 / (1 + candidate.active_orders),
                .15 * candidate.same_category_done / (candidate.same_category_done + 2),
                .15 * ((candidate.avg_score - 1) / 4 if candidate.avg_score is not None else .6),
            ]
            # Public avg_score rounds to 2dp; contribution sums may differ <0.001.
            assert abs(sum(row["contributions"]) - candidate.score) < .001
            rows.append(row)
        result["ranking"][category] = rows

    result["alerts"] = {"threshold_hours": settings.alert_threshold_hours,
                        "scan_interval_seconds": settings.alert_scan_interval_seconds,
                        "first_scan": alert_service.scan(db), "repeat_scan": alert_service.scan(db)}
    operator = db.scalars(select(User).where(User.role == UserRole.DEVICE_ADMIN)).first()
    actions = []
    for kind, action in ((AlertType.DISPATCH_TIMEOUT, OrderAction.DISPATCH),
                         (AlertType.REPAIR_TIMEOUT, OrderAction.URGE)):
        alert = db.scalars(select(OrderAlert).where(OrderAlert.alert_type == kind, OrderAlert.is_handled.is_(False))).first()
        assert alert is not None
        before = db.scalar(select(func.count()).select_from(OrderLog).where(OrderLog.order_id == alert.order_id, OrderLog.action == action))
        handled = alert_service.handle(db, operator, alert.id)
        after = db.scalar(select(func.count()).select_from(OrderLog).where(OrderLog.order_id == alert.order_id, OrderLog.action == action))
        assert after - before == 1
        actions.append({"type": kind.value, "order_id": alert.order_id, "action": action.value,
                        "new_logs": after - before, "note": handled.handle_note})
    result["alerts"]["actions"] = actions
    result["alerts"]["after_handling_scan"] = alert_service.scan(db)
    result["alerts"]["open_remaining"] = db.scalar(select(func.count()).select_from(OrderAlert).where(OrderAlert.is_handled.is_(False)))
    assert result["alerts"]["repeat_scan"]["created"] == 0
    assert result["alerts"]["after_handling_scan"]["created"] == 0

output = Path(__file__).with_name("dispatch-alerts.json")
output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(output.read_text())
