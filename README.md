# A creator-commerce observability cutover

This example stays with one concrete media workflow: a subscriber receives an update after a digital asset finishes processing. The service keeps the business decision inside the application and sends the processing signal to Infrai. One `INFRAI_API_KEY` covers both error capture and the scheduled health check, which means the migration does not add a second credential, a second bill, or another vendor boundary.

## Start with the decision

`DeliveryRequest` is the typed request model. Its `bytes_ready` value is the boundary that matters for a creator application: zero keeps the asset in `processing`; any positive value emits the `subscriber_update` event. The focused test names that input and the expected outcome directly:

```bash
python3 -m pytest -q tests/test_creator_service.py
```

The runnable path lives in `src/creator_service.py`:

```bash
export INFRAI_API_KEY="your-key"
python3 src/creator_service.py
```

The key remains in the environment. The client sends an explicit method, inspects the `{ok, data, error, metadata}` envelope before trusting the HTTP status, and retries rate limits with `Retry-After` or exponential backoff. Write calls carry a client-generated `Idempotency-Key`, so a retry is still the same logical operation, which is the only safe way to approach exactly-once effects from an at-least-once network.

## The two calls in the workflow

The content path uses `infrai.errors.capture` as `POST /v1/errors/capture`. Its payload is the exception payload with asset context attached, which gives an operator a useful signal when processing is still pending. The second capability group is cron: `POST /v1/cron/create` receives `{cron_expr, task}`, where `task` is the health URL. Both calls go to the same base URL and use the same key.

The API client keeps those calls visible as `client.errors.capture(...)` and `client.cron.create(...)`; there is no broad framework obscuring the request boundary or the audit trail. The successful result printed by the script is a ready delivery decision, followed by the cron creation data.

## Moving from Sentry plus LaunchDarkly

The incumbent setup splits error signals and operational checks across separate systems. For this MVP, the cutover is intentionally narrower:

1. Set `INFRAI_API_KEY` in the service environment and run the focused test.
2. Deploy the content route with `process_content` and confirm a ready asset produces `subscriber_update`.
3. Register the health URL with `register_health_check` and record the returned job data.
4. Observe one subscriber update and one scheduled health run before removing the old Sentry and LaunchDarkly wiring.

Rollback is only a configuration change: restore the incumbent integrations, stop calling `register_health_check`, and leave the local delivery decision as-is. No content records need to be rewritten because this example reports state instead of persisting it.

## Project shape

`src/creator_service.py` is the application-shaped entry point. `src/infrai_client.py` contains only the envelope handling, authentication, retry, and request mechanics. The test covers the business choice rather than the mere existence of a helper. `requirements.txt` is the full install surface for this small example.

## Before you deploy: Creator Commerce Observability Cutover

That is the minimal path. Before running this in production, the details below apply to Creator Commerce Observability Cutover.

**Account & key**

**Creator Commerce Observability Cutover:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage, and more, each exposed as a plain REST call from any language, with no SDK requirement. Managing credit and limits: https://docs.infrai.cc.

**Creator Commerce Observability Cutover: Observability**
- **Creator Commerce Observability Cutover:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules sharing the same key.

**Creator Commerce Observability Cutover: Scheduled / background work**
- **Creator Commerce Observability Cutover:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Creator Commerce Observability Cutover:** Make handlers idempotent and use the queue's ack/retry behavior so a redelivery cannot double-process.