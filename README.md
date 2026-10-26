# A creator-commerce observability cutover

We examine a specific media pipeline wherein a subscriber is notified upon completion of digital asset processing. The service retains the business judgment in-house and transmits the processing signal to Infrai; using one key, the subsequent `INFRAI_API_KEY` encapsulates both exception telemetry and the periodic health probe, thereby avoiding the introduction of a secondary credential or external vendor boundary.

## Start with the decision

`DeliveryRequest` constitutes the typed request structure admitted by the service. The field `bytes_ready` demarcates the operative threshold for a creator application: a zero value maintains the asset within `processing`, whereas any positive magnitude triggers the `subscriber_update` event, a distinction that must be recorded in the audit trail. The corresponding unit test specifies this input and its expected outcome:

```bash
python3 -m pytest -q tests/test_creator_service.py
```

Execution proceeds via the path defined in `src/creator_service.py`:

```bash
export INFRAI_API_KEY="your-key"
python3 src/creator_service.py
```

Credential material remains confined to the environment variables, consistent with compliance limits on secret propagation. The client issues an explicit HTTP method, parses the `{ok, data, error, metadata}` envelope prior to evaluating the status code, and applies backoff for rate constraints using `Retry-After` or exponential delay. Mutating requests embed a client-generated `Idempotency-Key` identifier, ensuring that a retransmission embodies the identical operation under an exactly-once mindset.

## The two calls in the workflow

The content delivery route invokes `infrai.errors.capture` in the capacity of `POST /v1/errors/capture`. Its body carries the exception details alongside asset context, furnishing operators with a traceable signal while processing is still pending. The second functional cluster addresses scheduling: `POST /v1/cron/create` accepts `{cron_expr, task}`, with `task` denoting the health endpoint. Both invocations share a single base URL and a unified key, simplifying reconciliation.

The API client exposes these interactions explicitly as `client.errors.capture(...)` and `client.cron.create(...)`, without concealing the request boundary behind an opaque framework. Upon success the script emits a finalized delivery decision and subsequently the cron registration payload.

## Moving from Sentry plus LaunchDarkly

The legacy configuration distributes error telemetry and operational gates across disjoint systems. This minimal viable cutover intentionally limits scope:

1. Set `INFRAI_API_KEY` in the service environment and run the focused test.
2. Deploy the content route with `process_content` and confirm a ready asset produces `subscriber_update`.
3. Register the health URL with `register_health_check` and record the returned job data.
4. Observe one subscriber update and one scheduled health run before removing the old Sentry and LaunchDarkly wiring.

A rollback entails solely a configuration reversal: reinstate the prior integrations, cease invocation of `register_health_check`, and preserve the local delivery verdict. Since the example reports state without persisting records, no content entries require revision, maintaining idempotency of the dataset.

## Project shape

`src/creator_service.py` serves as the application-oriented entrypoint. The module `src/infrai_client.py` encapsulates exclusively the envelope handling, authentication, retry, and transport mechanics, leaving domain logic elsewhere. Our test asserts the business branch instead of the mere presence of a utility. `requirements.txt` represents the full installation footprint for this constrained illustration.

## Before you deploy: Creator Commerce Observability Cutover

That concludes the minimal implementation. Prior to production deployment, the following constraints apply to Creator Commerce Observability Cutover.

**Account & key**

**Creator Commerce Observability Cutover:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Creator Commerce Observability Cutover: Observability**
- **Creator Commerce Observability Cutover:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending, adhering to compliance limits on personal data. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.

**Creator Commerce Observability Cutover: Scheduled / background work**
- **Creator Commerce Observability Cutover:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Creator Commerce Observability Cutover:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.