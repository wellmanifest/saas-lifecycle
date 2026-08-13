---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-001
---
# Participant: codex (AI agent)

## Understanding

The verified SaaS portal separates authenticated onboarding, billing-provider
confirmation, idempotent webhook intake and asynchronous provisioning. The
missing standard must make trial conversion, settlement currency, plan changes
and failure states explicit while keeping provider secrets and tenant target
coordinates outside the lifecycle document.

## Execution plan

1. Define provider-neutral offer, request, state and receipt variants.
2. Specify trial, subscription, plan-change and provisioning invariants.
3. Constrain lifecycle requests with a closed schema and matching GBNF.
4. Add dependency-free positive and adversarial conformance tests.
5. Validate locally, through the governance gate and in networkless Docker.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Adopted published `wellmanifest/new-project` v0.15.0 at its exact revision.
- Kept commercial lifecycle semantics separate from generic deployment and POA.
- Added closed offer, lifecycle request, authoritative state and receipt
  variants with an intentionally small request-only GBNF language.
- Made trial conversion, currency authority, provider verification, webhook
  idempotency and provisioning-outbox boundaries machine-testable.
- Added architecture/logic diagrams and a dependency-free conformance runner.
- Passed governance with zero findings, Draft 2020-12 metaschema validation,
  four positive variants, fifteen adversarial rejections, networkless Docker
  conformance and `git diff --check`.

## Blockers

- The initial-baseline blocker is resolved by the explicitly authorized local
  commit `73deba07f7c7300dd67f909f1496f605f39e20ed`.
- The user's explicit push request authorizes public remote creation,
  ticket-branch publication and pull-request creation for this bounded diff.
- New authority remains required for destructive action, secret access,
  material objective expansion and trusted merge.

## Risks and controls

- UI callbacks can falsely claim payment; only provider API verification or a
  verified webhook may advance billing state.
- A free trial can become an undisclosed charge; conversion policy is explicit
  and must create a user-visible notice boundary.
- Currency conversion can mislead; settlement and display amounts are separate.
- Provisioning retries can duplicate tenants; outbox and idempotency keys bind
  the exact account, plan and tenant reference.
