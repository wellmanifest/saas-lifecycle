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

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
