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
- Recorded the owner's “a powinny być” follow-up as explicit authorization to
  publish this branch, open a pull request and pursue its protected integration
  after exact-head trusted validation. It is not permission to bypass review.
- Reviewed the merged v1 schema, request grammar, conformance runner,
  architecture and logic-flow guidance against the action-priced Basic/Pro,
  PrePaid, localized-currency and separate On-Premise implementation.
- Added closed commercial models for flat and usage subscriptions, PrePaid
  add-ons and perpetual licences, plus Cloud/self-hosted/hybrid delivery modes.
  A generic versioned `metricRef` keeps actions, API calls, documents, devices
  and seats outside the lifecycle standard's metering authority.
- Replaced one implicit plan settlement with one or more unique versioned
  `priceRef` options. One stable plan can now expose monthly and annual prices;
  lifecycle requests, subscriptions, usage grants and receipts bind the exact
  selected option.
- Added `capabilityParityGroup` validation: peers must have equal entitlements,
  deployment mode and commercial kind but may differ by price and allowance.
- Made `purchase_addon` first-class. A compatible, one-time, never-reset
  allowance with explicit validity creates a server-verified usage grant and
  `addon_activated` receipt without replacing `currentPlanRef`.
- Bound indicative exchange rates to explicit base/quote currency pairs and
  added unique locale defaults with direct conversion coverage from every
  Cloud, licence and maintenance settlement currency.
- Added perpetual self-hosted/hybrid licensing with optional recurring
  maintenance, included periods and explicit renewal policy.
- Expanded the action grammar, architecture diagrams, state flow, top-up,
  currency-choice and maintenance guidance while retaining payment, metering,
  deployment and legal systems as external authorities.
- Fixed the conformance runner's pre-existing late-bound lambda defect, which
  previously let all adversarial closures reference the last test document.
  Thirty-two independently bound adversarial cases now prove the intended
  rejection paths.
- Passed Draft 2020-12 metaschema and positive-document validation, host and
  rebuilt networkless Docker conformance, Python compilation, diff hygiene and
  managed governance with identical schema and grammar digests.

## Blockers

- None. Validator run `31732066238` approved exact HEAD
  `73cd6ec175117b0749a05dbf6421d7e39c88af95` and merged pull request #2 as
  `88eb060e5a765913958612e128dbd444b37665d6`; the ticket is closed from the
  integrated default branch.
- New authority remains required for destructive action, secret access, new
  external coordination or material objective expansion.
