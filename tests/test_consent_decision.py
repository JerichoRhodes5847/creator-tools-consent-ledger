from creator_consent.consent_ledger import ConsentChange, ConsentDenied, ConsentService, ReleaseOperation, Scope


class AcceptedCaptcha:
    def verify(self, *, widget_record_id: str, token: str, action: str) -> dict[str, object]:
        assert widget_record_id == "widget-123"
        assert token == "browser-proof"
        assert action in {"consent_grant", "consent_revoke"}
        return {"verified": True}


def test_revocation_blocks_release_but_keeps_diagnostic_history() -> None:
    service = ConsentService(AcceptedCaptcha())
    service.grant(
        ConsentChange(
            user_id="editor-42",
            scopes={Scope.RELEASE_WRITE, Scope.DIAGNOSTICS_READ},
            captcha_token="browser-proof",
            widget_record_id="widget-123",
            operation_id="grant-episode-tools",
        )
    )
    service.record_release(
        ReleaseOperation(
            user_id="editor-42",
            project_id="daily-cut",
            release_id="episode-118",
            channel="public",
        )
    )
    service.revoke(
        ConsentChange(
            user_id="editor-42",
            scopes={Scope.RELEASE_WRITE},
            captcha_token="browser-proof",
            widget_record_id="widget-123",
            operation_id="revoke-publishing",
        )
    )

    try:
        service.record_release(
            ReleaseOperation(
                user_id="editor-42",
                project_id="daily-cut",
                release_id="episode-119",
                channel="public",
            )
        )
    except ConsentDenied as error:
        assert error.scope is Scope.RELEASE_WRITE
    else:
        raise AssertionError("release should require active user consent")

    kinds = [entry["kind"] for entry in service.diagnostics("editor-42")]
    assert kinds == ["granted", "release", "revoked"]


def test_repeated_grant_operation_returns_one_receipt_and_one_audit_entry() -> None:
    service = ConsentService(AcceptedCaptcha())
    change = ConsentChange(
        user_id="editor-42",
        scopes={Scope.BUILD_WRITE},
        captcha_token="browser-proof",
        widget_record_id="widget-123",
        operation_id="grant-build-tools",
    )

    first = service.grant(change)
    second = service.grant(change)

    assert first == second
    service.grant(
        ConsentChange(
            user_id="editor-42",
            scopes={Scope.DIAGNOSTICS_READ},
            captcha_token="browser-proof",
            widget_record_id="widget-123",
            operation_id="grant-diagnostics",
        )
    )
    kinds = [entry["kind"] for entry in service.diagnostics("editor-42")]
    assert kinds == ["granted", "granted"]
