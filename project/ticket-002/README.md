# Ticket 002: Standardize action-based offers and currency presentation

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-13

## Goal and scope

Extend the experimental provider-neutral SaaS lifecycle contract with the
commercial shapes proven necessary by a real offer implementation. The
standard currently models one settlement per plan and indicative display
quotes, but it cannot state that two plans have equal capabilities and differ
only by included usage, represent a time-limited PrePaid add-on without
replacing the tenant's base plan, or distinguish a self-hosted perpetual
licence and its optional maintenance from a Cloud subscription.

The update defines a generic versioned usage metric rather than hard-coding
"actions" or "seats". It covers recurring allowance packages, one-time usage
add-ons, capability-parity groups, Cloud/self-hosted delivery, usage grants and
add-on purchase receipts. It also removes the ambiguity of a display rate when
an offer contains plans with different settlement currencies by binding each
indicative quote to an explicit base/quote pair and mapping locales to default
presentation currencies. Settlement remains authoritative.

This work tightens the still-experimental v1 contract before a stable release.
It does not define how an action is metered, choose prices, publish exchange
rates, process a payment, calculate tax, or deploy customer infrastructure.

## Acceptance criteria

- [x] AC-01: Every plan declares a commercial type and deployment mode; the
      schema represents monthly/yearly price options, recurring usage
      allowances, time-limited one-time add-ons and perpetual self-hosted
      licences with optional maintenance.
- [x] AC-02: A capability-parity group guarantees equal entitlements while
      allowing plans to differ by price and included usage, so seat count is
      never an implicit pricing dimension.
- [x] AC-03: PrePaid purchase is a first-class lifecycle operation that adds a
      verified, expiring usage grant without replacing the current base plan,
      and receipts can report add-on activation.
- [x] AC-04: Every indicative conversion identifies base and quote currency,
      rate and date; locale defaults are unique, have conversion coverage and
      never override the authoritative settlement currency.
- [x] AC-05: Architecture and logic-flow guidance define selection, top-up,
      exhaustion, expiry, self-hosted maintenance and explicit currency-choice
      boundaries without assigning authority to the browser.
- [x] AC-06: Schema integrity, positive and adversarial conformance, networkless
      Docker validation, diff hygiene and managed governance all pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

## Authorization

The owner's request to update the standard from the implemented action-pricing
experience is recorded as `SESSION_EXECUTION_AUTHORIZATION`. It authorizes
planning, editing and local validation inside this ticket's intent without a
second confirmation. The follow-up “a powinny być” explicitly authorizes remote
branch publication, pull-request creation and pursuit of protected integration
into `main`. It does not bypass exact-head trusted review: merge authority must
still come from the repository's protected reviewer/validator boundary.
