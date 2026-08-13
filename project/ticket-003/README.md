# Ticket 003: Define payment and deployment mapping profiles

- **ID**: ticket-003
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-13

## Goal and scope

Define versioned, machine-validatable mapping profiles that connect the neutral
SaaS lifecycle to a payment adapter and a deployment adapter without moving
either provider's payload, credentials or state vocabulary into the core
contract. A profile maps declared operations, evidence fields, verified events,
idempotency and failure outcomes to the existing lifecycle boundaries.

The work supplies concrete PayPal REST and Plesk/Wellmanifest examples, but the
normative profile shape remains provider-neutral and supports other providers.
It does not call either provider, deploy a tenant, process a payment, prescribe
secrets, or make a provider response authoritative without server-side
verification.

## Acceptance criteria

- [x] AC-01: A closed Draft 2020-12 schema distinguishes payment and deployment
      mapping profiles and binds each profile, adapter and upstream contract by
      stable versioned references.
- [x] AC-02: Payment profiles declare create/inspect/capture/cancel and verified
      event bindings, exact offer checks, idempotency and reconciliation without
      embedding credentials or trusting a browser callback.
- [x] AC-03: Deployment profiles declare compile/authorize/apply/verify
      boundaries, durable outbox and idempotency bindings, bounded retries and
      redacted evidence without embedding hosts, users, docroots or grants.
- [x] AC-04: Concrete PayPal and Plesk/Wellmanifest examples validate while a
      second provider variant demonstrates that the schema does not encode one
      provider's field or event vocabulary as lifecycle authority.
- [x] AC-05: Positive and adversarial conformance rejects missing verification,
      unsafe secret/coordinate paths, ambiguous outcomes, unbounded retries and
      duplicate operation or event bindings.
- [x] AC-06: Neutrality guidance, host and networkless Docker conformance, diff
      hygiene and managed governance pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

## Authorization

The owner's “tak” in response to the remaining provider/deployment profile
roadmap item is recorded as `SESSION_EXECUTION_AUTHORIZATION`. It authorizes
planning, editing and local validation inside `intent.json` without a second
confirmation. It does not authorize provider calls, deployment, secret access,
external publication or trusted merge. The follow-up “kontynuuj” explicitly
authorizes publishing the exact ticket branch, opening its pull request and
pursuing protected integration into `main`. It does not replace exact-head
trusted approval or authorize a direct/bypass merge.

## Publication result

Pull request #3 was approved for exact HEAD
`2d4ffc98a586ab7f278e5da97a84c98a196dae49` by the repository-scoped
`ifuri-validator-agent` App and merged into `main` as
`1182915cc82270568607456fcefe8705796fac1a`. GitHub deleted the merged remote
ticket branch automatically. This governance-only closure is recorded from the
integrated default branch.
