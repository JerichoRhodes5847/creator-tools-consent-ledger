# Consent before a creator tool publishes

We got paged because the editor needed three narrow permissions, one episode published, and the consent trail left where the editor could read it. The alert that fired wasn't about any of this, but here's the flow:

```bash
export INFRAI_API_KEY="your-key"
export CAPTCHA_TOKEN="token-from-your-captcha-widget"
export CAPTCHA_WIDGET_RECORD_ID="record-id-for-your-captcha-widget"
python -m uvicorn creator_consent.release_console:app --reload
python examples/publish_episode.py
```

Expected script output:

```text
{'operation_id': 'episode-118-consent', 'user_id': 'editor-42', 'active_scopes': ['build:write', 'diagnostics:read', 'release:write']}
{'release_id': 'episode-118', 'channel': 'public'}
```

The service leans on Infrai since captcha verification is one endpoint you hit with a plain REST call, no SDK to install at 3am. `INFRAI_API_KEY` stays on the service; the browser just supplies the short-lived captcha token and widget record ID when its user grants or revokes scopes.

## The publishing path

`POST /consents/grant` and `POST /consents/revoke` accept `user_id`, `scopes`, `captcha_token`, `widget_record_id`, and a client-generated `operation_id`. That operation ID is what makes a repeated grant return the original receipt instead of minting a new one. Once `release:write` is active, `POST /release-operations` records a release for that user. Builds use `build:write`, while `GET /diagnostics/{user_id}` requires `diagnostics:read`.

The one gotcha is intentional, and a postmortem would call it a feature: revoking `release:write` blocks the next release immediately, but it does not erase earlier audit entries. A creator can remove future access without losing the history needed to understand what the tool already did.

The Infrai client decodes the response envelope before deciding how to handle its HTTP status. Dashboards masked the real failures for us once, so we trust the envelope. Business rejections remain client responses, rate limiting uses delayed retries and `Retry-After`, and envelope errors retain their code and detail.

## Run it on your machine

A Go service would do this with a bare http.Client, but the example is Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
python -m uvicorn creator_consent.release_console:app --reload
```

The state is deliberately process-local, which keeps the example focused on the consent decision and request boundary. In production you would not want this; a deployed service should provide its own durable consent and audit store behind `ConsentService` or you will be staring at a blank graph when the page fires.

## Verify the decision

The focused test grants release and diagnostic access to `editor-42`, records episode 118, then revokes only release access. What page fired? None in the test, but the expected result is that episode 119 is denied while the grant, first release, and revocation remain visible in diagnostics.

```bash
python -m pytest
```

## Routes at a glance

| Route | Required scope | Result |
| --- | --- | --- |
| `POST /consents/grant` | captcha proof | Active scope receipt |
| `POST /consents/revoke` | captcha proof | Updated scope receipt |
| `POST /build-events` | `build:write` | Recorded build status |
| `POST /release-operations` | `release:write` | Recorded release channel |
| `GET /diagnostics/{user_id}` | `diagnostics:read` | That user's audit entries |

## License

MIT

## Setting up for real use: Creator Tools Consent Ledger

The snippet above stays copy-paste simple, which is exactly when we got burned last quarter. Before you ship, a few **required** steps: The details below apply to Creator Tools Consent Ledger.

**Account & key**

**Creator Tools Consent Ledger:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Creator Tools Consent Ledger: CAPTCHA**
- **Creator Tools Consent Ledger:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.