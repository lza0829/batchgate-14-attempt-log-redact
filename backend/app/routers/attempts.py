import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import connect
from app.repositories import orchestrations as orch_repo
from app.repositories import redaction as redaction_repo

router = APIRouter(tags=["attempts"])


@router.get("/attempts")
def list_attempts(orchestration_id: int | None = None):
    conn = connect()
    try:
        return orch_repo.list_attempts(conn, orchestration_id)
    finally:
        conn.close()


@router.get("/attempts/export")
def export_attempts(orchestration_id: int | None = None):
    """Export attempt details as a downloadable JSON bundle with a manifest.

    Details are stored redacted (write path), so the export never contains
    cleartext sensitive values; the manifest lets a reviewer check that the
    bundle row count matches the attempt record count.
    """
    conn = connect()
    try:
        attempts = orch_repo.list_attempts(conn, orchestration_id)
        rules = redaction_repo.get_rules(conn)
    finally:
        conn.close()
    exported_at = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    payload = {
        "manifest": {
            "kind": "attempt_export",
            "exported_at": exported_at,
            "orchestration_id": orchestration_id,
            "attempt_count": len(attempts),
            "redaction": {
                "applied_at": "write",
                "rule_count": len(rules),
                "rules": rules,
            },
        },
        "attempts": attempts,
    }
    suffix = f"orch{orchestration_id}" if orchestration_id is not None else "all"
    filename = f"attempts-export-{suffix}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
