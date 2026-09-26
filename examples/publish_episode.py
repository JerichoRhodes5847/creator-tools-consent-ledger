from __future__ import annotations

import os

import httpx


def main() -> None:
    base = os.environ.get("CONSENT_SERVICE_URL", "http://127.0.0.1:8000")
    user_id = "editor-42"
    grant = httpx.request(
        method="POST",
        url=f"{base}/consents/grant",
        json={
            "user_id": user_id,
            "scopes": ["build:write", "release:write", "diagnostics:read"],
            "captcha_token": os.environ["CAPTCHA_TOKEN"],
            "widget_record_id": os.environ["CAPTCHA_WIDGET_RECORD_ID"],
            "operation_id": "episode-118-consent",
        },
    )
    grant.raise_for_status()
    print(grant.json())

    release = httpx.request(
        method="POST",
        url=f"{base}/release-operations",
        json={
            "user_id": user_id,
            "project_id": "daily-cut",
            "release_id": "episode-118",
            "channel": "public",
        },
    )
    release.raise_for_status()
    print(release.json())


if __name__ == "__main__":
    main()
