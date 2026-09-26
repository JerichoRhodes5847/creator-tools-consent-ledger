from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .consent_ledger import BuildEvent, ConsentChange, ConsentDenied, ConsentService, ReleaseOperation
from .infrai_captcha import InfraiCaptcha, InfraiError


def create_app(service: ConsentService | None = None) -> FastAPI:
    consent = service or ConsentService(InfraiCaptcha())
    app = FastAPI(title="Creator tools consent ledger")

    @app.exception_handler(InfraiError)
    async def infrai_error_handler(_, error: InfraiError) -> JSONResponse:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        return JSONResponse(status_code=status, content={"error": error.detail})

    @app.exception_handler(ConsentDenied)
    async def consent_error_handler(_, error: ConsentDenied) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"error": {"code": "CONSENT_REQUIRED", "message": str(error)}},
        )

    @app.post("/consents/grant")
    def grant(change: ConsentChange) -> dict[str, object]:
        return consent.grant(change)

    @app.post("/consents/revoke")
    def revoke(change: ConsentChange) -> dict[str, object]:
        return consent.revoke(change)

    @app.post("/build-events")
    def record_build(event: BuildEvent) -> dict[str, str]:
        return consent.record_build(event)

    @app.post("/release-operations")
    def record_release(operation: ReleaseOperation) -> dict[str, str]:
        return consent.record_release(operation)

    @app.get("/diagnostics/{user_id}")
    def diagnostics(user_id: str) -> dict[str, object]:
        return {"user_id": user_id, "entries": consent.diagnostics(user_id)}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
