---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-002
---
# Participant: codex (AI agent)

## Understanding

The current contract correctly separates authoritative settlement from an
indicative display quote, but the quote has no base currency and becomes
ambiguous when Cloud and On-Premise items settle in different currencies. A
plan also has no commercial kind, usage allowance, compatibility relation or
delivery mode, so PrePaid can only be misrepresented as another base plan.
The contract needs generic usage semantics and add-on lifecycle state while
retaining its provider, deployment, legal and metering authority boundaries.

## Execution plan

1. Extend the closed offer schema with generic usage, add-on, parity,
   deployment and maintenance terms.
2. Bind every display rate to base/quote currencies and add locale defaults.
3. Add purchase-add-on requests, verified usage grants and receipt outcomes.
4. Strengthen the dependency-free conformance runner with positive and
   adversarial cases for all new invariants.
5. Update architecture and logic flows, then validate on host, in networkless
   Docker and through managed governance.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Reviewed the merged v1 schema, request grammar, conformance runner,
  architecture and logic-flow guidance against the action-priced Basic/Pro,
  PrePaid, localized-currency and separate On-Premise implementation.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
