"""Reproduce presentation numbers on an explicitly isolated, seeded database.

Requires backend dependencies. Set DB_NAME, DB_USER, DB_PASSWORD externally.
This script refuses the application database and never creates/drops schemas.
"""
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.enums import OrderAction, OrderStatus, Urgency
from app.core.exceptions import BizError
from app.models import OrderLog, RepairOrder, User
from app.schemas import DispatchIn
from app.services import order_service
from app.services.ai import text as retrieval
from app.services.ai.diagnosis import local_diagnose
from app.services.ai.knowledge import knowledge_base
from scripts.eval_diagnosis import CASES, CONFIGS
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

if not settings.db_name.startswith("cyf_jxrepair_bench_"):
    raise SystemExit("DB_NAME must start with cyf_jxrepair_bench_; production is forbidden")


def summary(samples):
    ordered = sorted(samples)
    return {"median_ms": round(statistics.median(samples), 3),
            "p95_ms": round(ordered[int((len(ordered) - 1) * .95)], 3), "n": len(samples)}


def measure(call, n=40):
    samples = []
    for _ in range(n):
        start = time.perf_counter()
        call()
        samples.append((time.perf_counter() - start) * 1000)
    return summary(samples)


result = {"utc": datetime.now(UTC).isoformat(),
          "order_service_sha256": hashlib.sha256((ROOT / "backend/app/services/order_service.py").read_bytes()).hexdigest(),
          "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
          "python": platform.python_version(), "machine": platform.machine(),
          "cpu_count_visible": os.cpu_count(),
          "seed_sha256": hashlib.sha256((ROOT / "sql/02_seed.sql").read_bytes()).hexdigest(),
          "scope": "isolated seeded DB; synthetic corpus; algorithm microbenchmark, not HTTP capacity"}

with SessionLocal() as db:
    result["database"] = db.scalar(select(func.version()))
    knowledge_base._ensure(db)
    result["archived_cases"] = len(knowledge_base._cases)
    docs = [f"{c.fault_desc} {c.fault_desc} {c.fault_category or ''} {c.device_category} {c.repair_result}"
            for c in knowledge_base._cases]
    rows = []
    for name, options in CONFIGS:
        predictions = []
        # Production search always expands synonyms. Patch only the retrieval
        # module's lookup in this single-threaded experiment for a clean ablation.
        expand = retrieval.expand_synonyms if options["use_synonyms"] else lambda value: value
        with patch.object(retrieval, "expand_synonyms", expand):
            for query, expected in CASES:
                categories = [i.category for i in local_diagnose(db, query, **options)]
                predictions.append({"query": query, "expected": expected, "predicted": categories})
        rows.append({"name": name, "n": len(CASES),
                     "top1_correct": sum(bool(p["predicted"]) and p["predicted"][0] == p["expected"] for p in predictions),
                     "top3_correct": sum(p["expected"] in p["predicted"][:3] for p in predictions),
                     "covered": sum(bool(p["predicted"]) for p in predictions), "predictions": predictions})
    result["ablation"] = rows

result["retrieval"] = []
query = "夹爪夹不住工件，有嘶嘶声"
for size in (1000, 5000, 10000):
    # Repeat the 26 seeded cases with unique IDs: controlled scale, not real records.
    corpus = [f"{docs[i % len(docs)]} case{i:06d}" for i in range(size)]
    index = retrieval.Bm25Index(corpus)
    for _ in range(5):
        index.search(query)
    warm = measure(lambda index=index: index.search(query))
    cold = measure(lambda corpus=corpus: retrieval.Bm25Index(corpus).search(query))
    assert index.search(query) == retrieval.Bm25Index(corpus).search(query)
    result["retrieval"].append({"documents": size, "warm_query": warm, "rebuild_and_query": cold,
                                "median_speedup": round(cold["median_ms"] / warm["median_ms"], 2)})

rounds = []
for round_id in range(10):
    with SessionLocal() as db:
        order = RepairOrder(order_no=f"BENCH{round_id:09d}", device_id=4, reporter_id=5,
                            fault_desc="并发派单实验，仅隔离库", urgency=Urgency.NORMAL, status=OrderStatus.PENDING)
        db.add(order)
        db.commit()
        order_id = order.id
    barrier = Barrier(10)

    def dispatch(_, barrier=barrier, order_id=order_id):
        with SessionLocal() as db:
            user = db.get(User, 1)
            barrier.wait(timeout=20)
            try:
                order_service.dispatch(db, user, order_id, DispatchIn(repairer_id=12))
                return "success"
            except BizError as exc:
                db.rollback()
                return f"conflict_{exc.code}"
            except OperationalError as exc:
                db.rollback()
                return f"database_error_{exc.orig.args[0]}"

    with ThreadPoolExecutor(max_workers=10) as pool:
        outcomes = Counter(pool.map(dispatch, range(10)))
    with SessionLocal() as db:
        logs = db.scalar(select(func.count()).select_from(OrderLog).where(
            OrderLog.order_id == order_id, OrderLog.action == OrderAction.DISPATCH))
        state = db.get(RepairOrder, order_id).status.value
    rounds.append({"round": round_id + 1, "outcomes": dict(outcomes), "dispatch_logs": logs, "state": state})
    if os.getenv("BENCH_REQUIRE_CLEAN", "1") == "1":
        assert outcomes == {"success": 1, "conflict_409": 9} and logs == 1 and state == "ASSIGNED", rounds[-1]
result["concurrency"] = {"parallel_calls": 10, "rounds": rounds,
                         "scope": "service-layer calls; independent DB sessions; synchronized barrier; not HTTP load test"}
engine.dispose()
out = Path(__file__).with_name(os.getenv("BENCH_RESULT_FILE", "results.json"))
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("ablation", "concurrency")}, ensure_ascii=False, indent=2))
print("Top1:", [(r["name"], r["top1_correct"], r["n"]) for r in rows])
print("Concurrency:", [(r["outcomes"], r["dispatch_logs"]) for r in rounds])
