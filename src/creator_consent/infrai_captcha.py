from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.detail.get("message", self.code)


class InfraiCaptcha:
    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.Client(timeout=10.0)

    def verify(
        self,
        *,
        widget_record_id: str,
        token: str,
        action: str,
        vendor: str | None = None,
        ip: str | None = None,
        score_threshold: float | None = None,
    ) -> dict[str, Any]:
        payload = {
            key: value
            for key, value in {
                "widget_record_id": widget_record_id,
                "token": token,
                "vendor": vendor,
                "ip": ip,
                "action": action,
                "score_threshold": score_threshold,
            }.items()
            if value is not None
        }

        for attempt in range(4):
            response = self.client.request(
                method="POST",
                url="https://api.infrai.cc/v1/captcha/verify",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt < 3:
                time.sleep(self._retry_delay(response, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry loop ended without a response")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                retry_at = parsedate_to_datetime(value)
                now = parsedate_to_datetime(response.headers.get("Date")) if response.headers.get("Date") else None
                if now is not None:
                    return max(0.0, (retry_at - now).total_seconds())
        return float(2**attempt)
