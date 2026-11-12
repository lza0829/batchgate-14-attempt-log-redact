import json

import pytest

from app import db
from app.engines.redaction import MASK_PLACEHOLDER, normalize_rules, redact_value
from app.repositories import orchestrations as orch_repo
from app.repositories import redaction as redaction_repo
from app.routers.attempts import export_attempts
from app.seed import init_db
from app.services import orchestrate_service


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "DB_PATH", data_dir / "app.db")
    init_db()
    c = db.connect()
    yield c
    c.close()


def _latest_orch_id(conn) -> int:
    return conn.execute("SELECT MAX(id) i FROM orchestrations").fetchone()["i"]


def _details_blob(conn, orch_id: int) -> str:
    rows = conn.execute(
        "SELECT detail FROM job_attempts WHERE orchestration_id=?", (orch_id,)
    ).fetchall()
    return json.dumps([json.loads(r["detail"]) for r in rows], ensure_ascii=False)


def test_mask_by_field_name_at_any_depth():
    rules = normalize_rules([{"fields": ["customer_id"], "action": "mask"}])
    detail = {
        "ok": True,
        "sample": [
            {"customer_id": "C-1", "amount": 120.5},
            {"customer_id": "C-2", "amount": 88.0},
        ],
    }
    out = redact_value(detail, rules)
    assert out["sample"][0]["customer_id"] == MASK_PLACEHOLDER
    assert out["sample"][1]["customer_id"] == MASK_PLACEHOLDER
    assert out["sample"][0]["amount"] == 120.5
    # Original payload untouched.
    assert detail["sample"][0]["customer_id"] == "C-1"


def test_drop_removes_field():
    rules = normalize_rules([{"fields": ["phone"], "action": "drop"}])
    out = redact_value({"rows": [{"phone": "138", "name": "Ada"}]}, rules)
    assert out == {"rows": [{"name": "Ada"}]}


def test_dotted_path_and_disabled_rule():
    rules = normalize_rules(
        [
            {"fields": ["sample.amount"], "action": "mask"},
            {"fields": ["watermark_ts"], "action": "mask", "enabled": False},
        ]
    )
    out = redact_value({"watermark_ts": "2026-01-01", "sample": [{"amount": 1.5}]}, rules)
    assert out["sample"][0]["amount"] == MASK_PLACEHOLDER
    assert out["watermark_ts"] == "2026-01-01"


def test_normalize_rules_rejects_bad_input():
    with pytest.raises(ValueError):
        normalize_rules([{"fields": [], "action": "mask"}])
    with pytest.raises(ValueError):
        normalize_rules([{"fields": ["a"], "action": "shred"}])
    with pytest.raises(ValueError):
        normalize_rules("not-a-list")


def test_orchestration_write_path_redacts_and_counts_match(conn):
    redaction_repo.put_rules(
        conn,
        [
            {"fields": ["customer_id", "phone"], "action": "mask", "enabled": True},
            {"fields": ["name"], "action": "drop", "enabled": True},
        ],
    )
    conn.commit()

    result = orchestrate_service.run_orchestration()
    report = result["report"]
    orch_id = report["orchestration_id"]

    rows = conn.execute(
        "SELECT j.name AS job_name, a.detail FROM job_attempts a "
        "JOIN jobs j ON j.id=a.job_id WHERE a.orchestration_id=?",
        (orch_id,),
    ).fetchall()
    # Row count must equal the attempt record count of this run.
    assert len(rows) == report["attempt_count"] > 0

    blob = json.dumps([r["detail"] for r in rows], ensure_ascii=False)
    for secret in ("C-1", "C-2", "13800001111", "13900002222", "Ada", "Ben"):
        assert secret not in blob
    assert MASK_PLACEHOLDER in blob

    dim = next(r for r in rows if r["job_name"] == "dim_customer")
    sample = json.loads(dim["detail"])["sample"]
    assert all(row["customer_id"] == MASK_PLACEHOLDER for row in sample)
    assert all(row["phone"] == MASK_PLACEHOLDER for row in sample)
    assert all("name" not in row for row in sample)


def test_export_manifest_count_matches_attempts(conn):
    orchestrate_service.run_orchestration()
    resp = export_attempts()
    payload = json.loads(resp.body)
    manifest = payload["manifest"]
    db_count = conn.execute("SELECT COUNT(*) c FROM job_attempts").fetchone()["c"]
    assert manifest["attempt_count"] == db_count == len(payload["attempts"])
    assert manifest["redaction"]["rule_count"] >= 1
    blob = json.dumps(payload, ensure_ascii=False)
    assert "13800001111" not in blob and "Ada" not in blob


def test_rule_change_applies_to_next_run(conn):
    # Default rules mask customer_id / name / phone.
    orchestrate_service.run_orchestration()
    blob1 = _details_blob(conn, _latest_orch_id(conn))
    assert MASK_PLACEHOLDER in blob1
    assert "13800001111" not in blob1

    # Rules cleared: raw values are stored again.
    redaction_repo.put_rules(conn, [])
    conn.commit()
    orchestrate_service.run_orchestration()
    blob2 = _details_blob(conn, _latest_orch_id(conn))
    assert "C-1" in blob2 and "13800001111" in blob2

    # New rule: drop customer_id entirely.
    redaction_repo.put_rules(
        conn, [{"fields": ["customer_id"], "action": "drop", "enabled": True}]
    )
    conn.commit()
    orchestrate_service.run_orchestration()
    blob3 = _details_blob(conn, _latest_orch_id(conn))
    assert "customer_id" not in blob3
    assert "C-1" not in blob3


def test_list_attempts_response_is_redacted(conn):
    orchestrate_service.run_orchestration()
    attempts = orch_repo.list_attempts(conn)
    assert attempts
    blob = json.dumps(attempts, ensure_ascii=False)
    assert "13800001111" not in blob
    assert MASK_PLACEHOLDER in blob
