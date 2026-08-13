---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-003
---
# Participant: codex (AI agent)

## Understanding

The lifecycle contract deliberately treats billing and deployment as external
authorities, but implementers still need a safe, reviewable way to state how an
adapter obtains verified evidence and maps it to neutral operations. The mapping
must be data rather than executable provider code, must refer to upstream API
contracts by version, and must fail closed when a provider result cannot prove
the exact account, tenant, plan, price, amount, currency or deployment request.

## Execution plan

1. Define one closed discriminated schema for payment and deployment profiles.
2. Add concrete provider examples plus a provider-diversity neutrality case.
3. Extend dependency-free conformance with positive and adversarial profiles.
4. Document mapping, trust, reconciliation and redaction boundaries.
5. Run host, networkless Docker, diff and managed governance validation.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Reviewed the integrated lifecycle boundaries, the current Subactor PayPal
  adapter and controlled Plesk URI catalog, then checked the provider operations
  against current primary PayPal, Stripe and Plesk documentation.
- Added a closed Draft 2020-12 profile family with separate payment and
  deployment variants. Provider vocabulary is confined to profiles while the
  existing lifecycle schema and grammar remain byte-for-byte unchanged.
- Required seven payment operations, exact offer/account/tenant evidence,
  signature verification, authoritative resource inspection, event
  deduplication, out-of-order reconciliation and finite retry semantics.
- Required deployment compile, single-use authorization, apply, independent
  verification and rollback phases over one durable outbox idempotency key.
  Coordinates and authorization material remain external bindings.
- Added validated PayPal Orders/Subscriptions/Webhooks, Stripe
  PaymentIntents/Subscriptions/Webhooks and Subactor Plesk/Wellmanifest
  deployment examples.
- Extended dependency-free conformance with profile digests, three positive
  adapter variants and thirteen new adversarial cases. Host and rebuilt
  networkless Docker runs reject all 45 total adversarial cases.
- Added neutral-review guidance with trust-boundary diagrams and explicit
  instructions for adding another provider without changing the lifecycle
  state machine.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- The implementation is locally complete and is now `IN_PROGRESS / PUBLICATION`.
  The owner's follow-up “kontynuuj” authorizes branch publication, pull-request
  creation and pursuit of protected integration after exact-head validation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge outside
  the protected repository boundary.
