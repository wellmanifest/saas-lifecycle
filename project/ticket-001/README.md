# Ticket 001: Define multi-tenant SaaS lifecycle standard

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: BLOCKED
- **Workflow state**: PLAN
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

- [ ] AC-01: A closed Draft 2020-12 schema defines offer, lifecycle request,
  lifecycle state and receipt document variants.
- [ ] AC-02: A trial declares duration, payment-method policy, conversion plan
  and conversion boundary; no silent charge or implicit plan is allowed.
- [ ] AC-03: Settlement currency is authoritative while localized display
  currencies are explicitly indicative and timestamped.
- [ ] AC-04: GBNF accepts only the request AST intersection and adversarial
  tests reject credential material, client-trusted payment state, raw tenant
  coordinates, unsigned events and duplicate provisioning.
- [ ] AC-05: Subscription confirmation is server-side, webhook processing is
  signature-verified and idempotent, and provisioning uses a durable outbox.
- [ ] AC-06: Architecture and logic flow contain Mermaid diagrams and map to
  POA, DSL and deployment without duplicating their authority contracts.
- [ ] AC-07: Governance, metaschema, positive/adversarial conformance and
  isolated networkless Docker validation pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

## Authorization

The request to continue and create missing standards is recorded as
`SESSION_EXECUTION_AUTHORIZATION` for `intent.json`. It is not trusted merge
approval and does not authorize payment-provider calls, customer contact,
remote deployment or credential access.

## Current blocker

The repository has no initial Git commit. Before implementation, bounded
delivery must bind a real `acceptedBaseSha`; creating that baseline requires
explicit commit authority. No implementation files or placeholder SHA were
created for this standard.
