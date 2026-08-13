# Ticket 001: Define multi-tenant SaaS lifecycle standard

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-12

## Goal and scope

Define a reusable lifecycle standard for multi-tenant SaaS signup, free or paid
trial, recurring subscription, plan change, verified billing events, tenant
provisioning and terminal receipts. It generalizes the portal implementation
without coupling the contract to PayPal, a specific ingress, currency display
or deployment engine.

The standard owns lifecycle semantics only. Authentication, payment providers,
tax/legal policy, tenant deployment and DNS/TLS execution remain external
capabilities governed by their own contracts.

## Acceptance criteria

- [x] AC-01: A closed Draft 2020-12 schema defines offer, lifecycle request,
  lifecycle state and receipt document variants.
- [x] AC-02: A trial declares duration, payment-method policy, conversion plan
  and conversion boundary; no silent charge or implicit plan is allowed.
- [x] AC-03: Settlement currency is authoritative while localized display
  currencies are explicitly indicative and timestamped.
- [x] AC-04: GBNF accepts only the request AST intersection and adversarial
  tests reject credential material, client-trusted payment state, raw tenant
  coordinates, unsigned events and duplicate provisioning.
- [x] AC-05: Subscription confirmation is server-side, webhook processing is
  signature-verified and idempotent, and provisioning uses a durable outbox.
- [x] AC-06: Architecture and logic flow contain Mermaid diagrams and map to
  POA, DSL and deployment without duplicating their authority contracts.
- [x] AC-07: Governance, metaschema, positive/adversarial conformance and
  isolated networkless Docker validation pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

## Authorization

The request to continue and create missing standards is recorded as
`SESSION_EXECUTION_AUTHORIZATION` for `intent.json`. It is not trusted merge
approval. The later explicit request to push the changes authorizes creation
of the public repository, committing this bounded diff, pushing its ticket
branch and opening a pull request. It does not authorize payment-provider
calls, customer contact, remote deployment or credential access.

## Baseline resolution

The user explicitly authorized a local, non-published baseline commit. Bounded
delivery now binds `acceptedBaseSha` to
`73deba07f7c7300dd67f909f1496f605f39e20ed`; no placeholder SHA or policy
bypass was used.

## Publication validation

Host and networkless Docker conformance passed with four positive variants and
15 adversarial rejections. Governance passed with zero errors and warnings,
and diff hygiene passed. Trusted exact-head review and merge remain pending
after ticket-branch publication.
