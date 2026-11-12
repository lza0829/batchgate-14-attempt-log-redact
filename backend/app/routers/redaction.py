from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import connect
from app.repositories import redaction as redaction_repo

router = APIRouter(tags=["redaction"])


class RulesBody(BaseModel):
    rules: list[dict[str, Any]]


@router.get("/redaction-rules")
def get_redaction_rules():
    conn = connect()
    try:
        return {"rules": redaction_repo.get_rules(conn)}
    finally:
        conn.close()


@router.put("/redaction-rules")
def put_redaction_rules(body: RulesBody):
    conn = connect()
    try:
        try:
            clean = redaction_repo.put_rules(conn, body.rules)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        conn.commit()
        return {"rules": clean}
    finally:
        conn.close()
