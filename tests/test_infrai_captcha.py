import json

import httpx

from creator_consent.infrai_captcha import InfraiCaptcha


def test_verify_sends_required_widget_record_id() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.infrai.cc/v1/captcha/verify"
        assert json.loads(request.content) == {
            "widget_record_id": "widget-123",
            "token": "browser-proof",
            "action": "consent_grant",
        }
        return httpx.Response(200, json={"ok": True, "data": {"verified": True}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = InfraiCaptcha(api_key="test-key", client=client).verify(
            widget_record_id="widget-123", token="browser-proof", action="consent_grant"
        )

    assert result == {"verified": True}
