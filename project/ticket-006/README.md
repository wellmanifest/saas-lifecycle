# Ticket 006: Standardize attributable usage settlement receipts

- **ID**: ticket-006
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-02

## Goal and scope

Add an append-only, provider-neutral usage ledger entry to the experimental
SaaS lifecycle contract. Each entry must correlate commercial account and
package identity with explicit organization/project/ticket attribution,
principal, process run, URI Process attempt, versioned metric and independent
authority evidence. It must support reserve, settle, release, waive and refund
without implying that authentication, an authority grant or a lease is itself
a commercial charge.

The request to execute and publish this standards-first work is recorded as
`SESSION_EXECUTION_AUTHORIZATION`. Protected exact-head approval remains the
only merge authority.

## Acceptance criteria

- [x] AC-01: A closed v1 usage-ledger entry represents the complete attribution
      chain and versioned metric/package identity without product pricing.
- [x] AC-02: Reserve/settle/release/waive/refund semantics are deterministic,
      idempotent per entry and keep operation outcome separate from charging.
- [x] AC-03: Authority grant, delegation and lease evidence is correlated but
      never treated as entitlement or settlement.
- [x] AC-04: Positive and adversarial conformance plus governance pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
