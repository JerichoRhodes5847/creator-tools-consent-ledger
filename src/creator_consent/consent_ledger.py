from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field


class Scope(StrEnum):
    BUILD_WRITE = "build:write"
    RELEASE_WRITE = "release:write"
    DIAGNOSTICS_READ = "diagnostics:read"


class ConsentChange(BaseModel):
    user_id: str = Field(min_length=1)
    scopes: set[Scope] = Field(min_length=1)
    captcha_token: str = Field(min_length=1)
    widget_record_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class BuildEvent(BaseModel):
    user_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    build_id: str = Field(min_length=1)
    status: str = Field(pattern="^(queued|running|succeeded|failed)$")


class ReleaseOperation(BaseModel):
    user_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    channel: str = Field(pattern="^(preview|public)$")


class ConsentDenied(Exception):
    def __init__(self, user_id: str, scope: Scope) -> None:
        self.user_id = user_id
        self.scope = scope
        super().__init__(f"{user_id} has not granted {scope}")


@dataclass(frozen=True)
class AuditEntry:
    kind: str
    user_id: str
    detail: str
    recorded_at: str


class ConsentService:
    def __init__(self, captcha: Any) -> None:
        self._captcha = captcha
        self._grants: dict[str, set[Scope]] = {}
        self._audit: list[AuditEntry] = []
        self._receipts: dict[str, dict[str, object]] = {}
        self._lock = Lock()

    def grant(self, change: ConsentChange) -> dict[str, object]:
        self._captcha.verify(widget_record_id=change.widget_record_id, token=change.captcha_token, action="consent_grant")
        return self._change(change, grant=True)

    def revoke(self, change: ConsentChange) -> dict[str, object]:
        self._captcha.verify(widget_record_id=change.widget_record_id, token=change.captcha_token, action="consent_revoke")
        return self._change(change, grant=False)

    def record_build(self, event: BuildEvent) -> dict[str, str]:
        self._require(event.user_id, Scope.BUILD_WRITE)
        self._append("build", event.user_id, f"{event.project_id}:{event.build_id}:{event.status}")
        return {"build_id": event.build_id, "status": event.status}

    def record_release(self, operation: ReleaseOperation) -> dict[str, str]:
        self._require(operation.user_id, Scope.RELEASE_WRITE)
        self._append(
            "release",
            operation.user_id,
            f"{operation.project_id}:{operation.release_id}:{operation.channel}",
        )
        return {"release_id": operation.release_id, "channel": operation.channel}

    def diagnostics(self, user_id: str) -> list[dict[str, str]]:
        self._require(user_id, Scope.DIAGNOSTICS_READ)
        return [entry.__dict__ for entry in self._audit if entry.user_id == user_id]

    def _change(self, change: ConsentChange, *, grant: bool) -> dict[str, object]:
        with self._lock:
            if change.operation_id in self._receipts:
                return self._receipts[change.operation_id]

            current = self._grants.setdefault(change.user_id, set())
            current.update(change.scopes) if grant else current.difference_update(change.scopes)
            verb = "granted" if grant else "revoked"
            scope_names = sorted(scope.value for scope in change.scopes)
            self._append(verb, change.user_id, ",".join(scope_names))
            receipt: dict[str, object] = {
                "operation_id": change.operation_id,
                "user_id": change.user_id,
                "active_scopes": sorted(scope.value for scope in current),
            }
            self._receipts[change.operation_id] = receipt
            return receipt

    def _require(self, user_id: str, scope: Scope) -> None:
        if scope not in self._grants.get(user_id, set()):
            raise ConsentDenied(user_id, scope)

    def _append(self, kind: str, user_id: str, detail: str) -> None:
        self._audit.append(
            AuditEntry(
                kind=kind,
                user_id=user_id,
                detail=detail,
                recorded_at=datetime.now(timezone.utc).isoformat(),
            )
        )
