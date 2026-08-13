# Ticket Changelog (ticket-002)

## [0.1.0] - 2026-08-13

- Initial governance scaffold created.
- No human participant identity or content was generated.

## [0.2.0] - 2026-08-13

### Added
- Generic recurring usage allowances, expiring PrePaid add-ons, verified usage
  grants and separate perpetual self-hosted licensing with maintenance policy.
- Multiple unique monthly/yearly `priceRef` options under one stable plan.
- Capability-parity groups for plans that differ by price/allowance, not access.
- Locale currency defaults and dated direct base/quote conversion pairs.
- `purchase_addon`, `addon_payment_completed` and `addon_activated` lifecycle
  vocabulary in the schema, request grammar, state and receipts.

### Changed
- Extended architecture and logic guidance for usage exhaustion, top-ups,
  currency selection, mixed settlement currencies and maintenance renewal.
- Bound every adversarial conformance closure to its own document, then expanded
  the suite from 15 nominal cases to 32 independently verified rejections.
